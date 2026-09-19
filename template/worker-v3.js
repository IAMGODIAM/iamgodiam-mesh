// iamgodiam-mesh v3 — live R2-backed mirror of github.com/IAMGODIAM/iamgodiam-mesh
// Hourly cron crawls the repo via raw.githubusercontent.com (no GitHub API, no rate limits),
// mirrors every internally-linked file into R2. Keyed POST /_sync forces a pass.
//
// v3 changes (Sovereign Knowledge Mesh war room, 2026-09-19):
// - Cursor-based sync: each pass processes up to PASS_LIMIT files and persists the
//   frontier in R2 (_sync_state.json). No more 150-file hard cap per cycle, and prune
//   only runs when a FULL cycle completes — the live mirror can finally hold all 10k pages.
// - Real /robots.txt: Cloudflare content-signals text preserved byte-identical, plus
//   Sitemap line. (Previously /robots.txt soft-404'd to the index page.)
// - Real /sitemap.xml generated from the mirror index. (Previously soft-404'd.)
// - /llms.txt: machine-readable cluster map for AI agents. (Previously soft-404'd.)
// - Unknown paths now return a real 404 page (kills the infinite soft-404 space,
//   the single most dangerous SEO defect on the domain).
// - Sync extracts per-page title/description into _index.json, powering sitemap/llms.txt.

const REPO = "IAMGODIAM/iamgodiam-mesh";
const BRANCH = "main";
const RAW = "https://raw.githubusercontent.com/" + REPO + "/" + BRANCH + "/";
const ORIGIN = "https://mesh.iamgodiam.net";
const PASS_LIMIT = 200; // files fetched per scheduled pass (cron CPU-safe)

const TYPES = {
  html: "text/html; charset=utf-8", css: "text/css", js: "application/javascript",
  json: "application/json", png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg",
  svg: "image/svg+xml", ico: "image/x-icon", webp: "image/webp", gif: "image/gif",
  txt: "text/plain; charset=utf-8", xml: "application/xml", pdf: "application/pdf",
  woff2: "font/woff2", woff: "font/woff", mp3: "audio/mpeg", mp4: "video/mp4"
};

// Cloudflare content-signals robots text — BYTE-IDENTICAL, sacred. Append-only below it.
const ROBOTS_SIGNALS = `# As a condition of accessing this website, you agree to abide by the following
# content signals:

# (a)  If a content-signal = yes, you may collect content for the corresponding
#      use.
# (b)  If a content-signal = no, you may not collect content for the
#      corresponding use.
# (c)  If the website operator does not include a content signal for a
#      corresponding use, the website operator neither grants nor restricts
#      permission via content signal with respect to the corresponding use.

# The content signals and their meanings are:

# search:   building a search index and providing search results (e.g., returning
#           hyperlinks and short excerpts from your website's contents). Search does not
#           include providing AI-generated search summaries.
# ai-input: inputting content into one or more AI models (e.g., retrieval
#           augmented generation, grounding, or other real-time taking of content for
#           generative AI search answers).
# ai-train: training or fine-tuning AI models.

# ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE EXPRESS RESERVATIONS OF
# RIGHTS UNDER ARTICLE 4 OF THE EUROPEAN UNION DIRECTIVE 2019/790 ON COPYRIGHT
# AND RELATED RIGHTS IN THE DIGITAL SINGLE MARKET.
`;

function ctype(key) {
  const e = key.includes(".") ? key.split(".").pop().toLowerCase() : "html";
  return TYPES[e] || "application/octet-stream";
}

function extractLinks(html) {
  const out = new Set();
  const re = /(?:href|src)\s*=\s*["']([^"']+)["']/gi;
  let m;
  while ((m = re.exec(html))) {
    let l = m[1].split("#")[0].split("?")[0].trim();
    if (l) out.add(l);
  }
  return [...out];
}

function extractMeta(html) {
  const t = html.match(/<title[^>]*>([\s\S]{0,200}?)<\/title>/i);
  const d = html.match(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']{0,300})/i)
         || html.match(/<meta[^>]+content=["']([^"']{0,300})["'][^>]+name=["']description["']/i);
  return {
    title: t ? t[1].replace(/\s+/g, " ").trim().slice(0, 160) : "",
    desc: d ? d[1].replace(/\s+/g, " ").trim().slice(0, 300) : ""
  };
}

function normalize(link, fromDir) {
  if (/^(https?:)?\/\//i.test(link)) return null;
  if (/^(mailto:|tel:|data:|javascript:|itms)/i.test(link)) return null;
  let p = link.startsWith("/") ? link.slice(1) : (fromDir ? fromDir + "/" : "") + link;
  const parts = [];
  for (const seg of p.split("/")) {
    if (!seg || seg === ".") continue;
    if (seg === "..") { parts.pop(); continue; }
    parts.push(seg);
  }
  p = parts.join("/");
  if (!p) return null;
  if (p.endsWith("/")) p += "index.html";
  return p;
}

// Keys the worker itself generates — never mirrored from the repo, never pruned.
const SELF_KEYS = new Set(["_sync.json", "_sync_state.json", "_index.json"]);

// Stale repo files the worker generates live instead (wrong host / incomplete).
const SKIP_MIRROR = new Set(["robots.txt", "sitemap.xml", "CNAME"]);

async function loadState(env) {
  const s = await env.MESH.get("_sync_state.json");
  if (s) {
    try { return JSON.parse(await s.text()); } catch (e) { /* fall through */ }
  }
  return { cycle: 1, queue: ["index.html"], seen: [], files: {}, misses: [], started_at: new Date().toISOString() };
}

async function saveState(env, st) {
  await env.MESH.put("_sync_state.json", JSON.stringify(st), { httpMetadata: { contentType: "application/json" } });
}

async function syncPass(env) {
  const t0 = Date.now();
  const st = await loadState(env);
  const seen = new Set(st.seen);
  const queue = st.queue;
  let fetched = 0;
  const misses = [];

  while (queue.length && fetched < PASS_LIMIT) {
    const key = queue.shift();
    if (seen.has(key) || SELF_KEYS.has(key) || SKIP_MIRROR.has(key)) continue;
    seen.add(key);
    let r;
    try {
      r = await fetch(RAW + key, { headers: { "user-agent": "iamgodiam-mesh-sync" } });
    } catch (e) { misses.push(key); continue; }
    if (!r.ok) { misses.push(key); continue; }
    const ct = ctype(key);
    if (ct.startsWith("text/html")) {
      // The site was authored at the apex — rewrite absolute self-links to root-relative
      // so the mirror is self-contained on mesh.iamgodiam.net.
      let html = await r.text();
      html = html.replace(/https?:\/\/(www\.|mesh\.)?iamgodiam\.net\//gi, "/");
      html = html.replace(/https?:\/\/(www\.|mesh\.)?iamgodiam\.net(["'])/gi, "/$2");
      await env.MESH.put(key, html, { httpMetadata: { contentType: ct } });
      const meta = extractMeta(html);
      st.files[key] = { t: meta.title, d: meta.desc };
      fetched++;
      const dir = key.includes("/") ? key.slice(0, key.lastIndexOf("/")) : "";
      for (const l of extractLinks(html)) {
        const n = normalize(l, dir);
        if (n && !seen.has(n) && !queue.includes(n)) queue.push(n);
      }
    } else {
      await env.MESH.put(key, r.body, { httpMetadata: { contentType: ct } });
      fetched++;
    }
  }

  st.seen = [...seen];
  st.queue = queue;
  st.misses = misses.slice(0, 20);

  let cycleComplete = false;
  let pruned = 0;
  if (queue.length === 0) {
    // Full cycle complete: publish the index, then prune leavers.
    cycleComplete = true;
    const idx = {
      at: new Date().toISOString(),
      cycle: st.cycle,
      pages: Object.keys(st.files).length,
      files: st.files
    };
    await env.MESH.put("_index.json", JSON.stringify(idx), { httpMetadata: { contentType: "application/json" } });
    const keep = new Set([...Object.keys(st.files), ...SELF_KEYS]);
    // keep non-html assets discovered this cycle too
    let cursor;
    do {
      const l = await env.MESH.list({ cursor });
      for (const o of l.objects) {
        if (!keep.has(o.key) && !o.key.endsWith(".css") && !o.key.endsWith(".js") && !o.key.endsWith(".png") && !o.key.endsWith(".jpg") && !o.key.endsWith(".svg") && !o.key.endsWith(".ico") && !o.key.endsWith(".webp")) {
          await env.MESH.delete(o.key); pruned++;
        }
      }
      cursor = l.truncated ? l.cursor : undefined;
    } while (cursor);
    // fresh cycle
    st.cycle += 1;
    st.queue = ["index.html"];
    st.seen = [];
    st.files = {};
    st.started_at = new Date().toISOString();
  }

  await saveState(env, st);
  const stamp = {
    at: new Date().toISOString(), cycle: st.cycle, fetched,
    queue: st.queue.length, seen: st.seen.length,
    cycle_complete: cycleComplete, pruned,
    misses: st.misses, ms: Date.now() - t0, repo: REPO, branch: BRANCH
  };
  await env.MESH.put("_sync.json", JSON.stringify(stamp), { httpMetadata: { contentType: "application/json" } });
  return stamp;
}

async function getIndex(env) {
  const i = await env.MESH.get("_index.json");
  if (i) { try { return JSON.parse(await i.text()); } catch (e) {} }
  return null;
}

function escXml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function serveSitemap(env) {
  const idx = await getIndex(env);
  let urls = [];
  if (idx && idx.files) {
    for (const key of Object.keys(idx.files)) {
      if (!key.endsWith(".html")) continue;
      const loc = key === "index.html" ? ORIGIN + "/" : ORIGIN + "/" + key;
      urls.push(`  <url><loc>${escXml(loc)}</loc></url>`);
    }
  } else {
    // index not built yet — list R2 directly
    let cursor;
    do {
      const l = await env.MESH.list({ cursor });
      for (const o of l.objects) {
        if (!o.key.endsWith(".html") || SELF_KEYS.has(o.key)) continue;
        const loc = o.key === "index.html" ? ORIGIN + "/" : ORIGIN + "/" + o.key;
        urls.push(`  <url><loc>${escXml(loc)}</loc></url>`);
      }
      cursor = l.truncated ? l.cursor : undefined;
    } while (cursor);
  }
  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join("\n")}\n</urlset>`;
  return new Response(xml, { headers: { "content-type": "application/xml", "cache-control": "public, max-age=3600" } });
}

async function serveLlms(env) {
  const idx = await getIndex(env);
  const lines = [
    "# IAMGODIAM — Sovereign Knowledge Mesh",
    "",
    "> The world's first Black-first, agentic-generated sovereign knowledge architecture.",
    "> Authority anchor: the Abba Talk book corpus (30,316 passages) at https://iamgodiam.net/book",
    "> Corpus API: https://iamgodiam.net/api/book/search?q=, /api/passage?id=, /api/book/toc",
    "",
    "## Clusters",
    ""
  ];
  if (idx && idx.files) {
    const hubs = Object.keys(idx.files).filter(k => /cluster-[^/]+\.html$/.test(k)).sort();
    for (const h of hubs) {
      const m = idx.files[h];
      lines.push(`- [${m.t || h}](${ORIGIN}/${h})${m.d ? " — " + m.d : ""}`);
    }
    lines.push("", `## Index`, "", `Full page index: ${ORIGIN}/sitemap.xml (${Object.keys(idx.files).length} pages, cycle ${idx.cycle}, ${idx.at})`);
  } else {
    lines.push("- Index is building — see " + ORIGIN + "/sitemap.xml");
  }
  return new Response(lines.join("\n") + "\n", { headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "public, max-age=3600" } });
}

async function serve404(env) {
  const idx = await getIndex(env);
  let hubs = [];
  if (idx && idx.files) {
    hubs = Object.keys(idx.files).filter(k => /cluster-[^/]+\.html$/.test(k)).sort().slice(0, 20);
  }
  const hubLinks = hubs.map(h => {
    const m = idx.files[h];
    return `<li><a href="/${h}">${escXml(m.t || h)}</a></li>`;
  }).join("\n");
  const html = `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Not found — IAMGODIAM Knowledge Mesh</title><meta name="robots" content="noindex"><style>*{box-sizing:border-box;margin:0;padding:0}body{background:#070710;color:#e8d5a3;font-family:Georgia,serif;line-height:1.8;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem}a{color:#c9a84c}</style></head><body><main style="max-width:640px;text-align:center"><h1>That page isn't in the Mesh.</h1><p>The Sovereign Knowledge Mesh holds thousands of pages across knowledge clusters — but not this address.</p><p><a href="/">Return to the Mesh home</a></p>${hubLinks ? `<h2 style="margin-top:2rem">Knowledge clusters</h2><ul style="list-style:none">${hubLinks}</ul>` : ""}</main></body></html>`;
  return new Response(html, { status: 404, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=300" } });
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(syncPass(env));
  },
  async fetch(req, env, ctx) {
    const u = new URL(req.url);
    const p = u.pathname;

    if (p === "/_sync") {
      if (req.method === "POST") {
        if ((req.headers.get("x-mesh-key") || "") !== env.SYNC_KEY)
          return new Response(JSON.stringify({ error: "key" }), { status: 403, headers: { "content-type": "application/json" } });
        const stamp = await syncPass(env);
        return new Response(JSON.stringify(stamp), { headers: { "content-type": "application/json" } });
      }
      const s = await env.MESH.get("_sync.json");
      return new Response(s ? await s.text() : "{}", { headers: { "content-type": "application/json" } });
    }

    if (p === "/robots.txt") {
      const txt = ROBOTS_SIGNALS + "\nSitemap: " + ORIGIN + "/sitemap.xml\n";
      return new Response(txt, { headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "public, max-age=3600" } });
    }
    if (p === "/sitemap.xml") return serveSitemap(env);
    if (p === "/llms.txt") return serveLlms(env);

    let key = decodeURIComponent(p).replace(/^\/+/, "");
    if (!key) key = "index.html";
    let obj = await env.MESH.get(key);
    if (!obj && !key.includes(".")) obj = await env.MESH.get(key + ".html");
    if (!obj && !key.includes(".")) obj = await env.MESH.get(key + "/index.html");
    if (!obj) return serve404(env);
    const ct = (obj.httpMetadata && obj.httpMetadata.contentType) || ctype(key);
    return new Response(obj.body, { headers: { "content-type": ct, "cache-control": "public, max-age=300" } });
  }
};