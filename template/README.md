# Sovereign Mesh Template — the replicable system

This directory is the whole page-network system in a box. To launch it on a new
site: copy this directory, write a cluster spec, generate, gate, deploy.

## The machinery (all of it runs — nothing here is documentation-only)

| File | What it does |
|---|---|
| `generate_cluster.py` | Page + hub generator. Input: cluster spec JSON. Output: HTML files implementing the page contract (question H1, direct-answer lede, 300+ distinct words, unique title/description/canonical, FAQPage + BreadcrumbList JSON-LD, hub/sibling/corpus links, freshness date). |
| `qa_gate.py` | The distinctiveness gate. Fails the build on: duplicate titles/descriptions/H1s, body-text Jaccard > 0.55 between any two pages, < 300 body words, missing JSON-LD, < 3 internal links, missing hub link, missing canonical, noindex. Run it before every deploy. |
| `pilot-cluster.json` | The worked example: "The Justice Reader" — 6 pages, each one canonical question answered from real Abba Talk corpus passages. Copy its schema for new clusters. |
| `worker-v3.js` | The serving layer (deployed as the `iamgodiam-mesh` Cloudflare Worker): cursor-based full-corpus sync, real `/robots.txt` (content-signals preserved byte-identical), generated `/sitemap.xml`, `/llms.txt`, real 404s (no soft-404 space). |

## The pipeline

1. **Spec** — one JSON per cluster: hub title/description + pages[{slug, stitle, question, answer, answer_html, corpus[{pid, quote, ref}], sections[{h, body_html}]}].
   Content rule: every page must be genuinely useful and distinct. Quotes must be verbatim
   corpus passages (verify via `/api/passage?id=`), commentary must be original.
2. **Generate** — `python3 generate_cluster.py my-cluster.json out/`
3. **Gate** — `python3 qa_gate.py --dir out/` — must print PASS (exit 0). Fix content, not the gate.
4. **Deploy** — commit `out/*.html` to `pages/`, link the hub from the index cluster grid.
   The mirror worker picks it up on the next hourly sync.
5. **Verify** — fetch the live URLs: 200s, sitemap includes them, QA-gate a live sample.

## Design rules (from the 2026-09-19 war room)

- One canonical question per page; the direct answer in the first 100–150 words.
- Every page cites the corpus it serves (passage quotes + links), never competes with it.
- Hub-and-spoke interlinking: leaves link up to the hub and sideways to siblings;
  hubs link down to every leaf. This is the backlink infrastructure — internal, legitimate.
- The AI-crawler content-signals robots text is byte-identical sacred: append only.
- Never ship a page the QA gate fails. Scaled thin content is a spam-policy violation,
  not a growth strategy.
