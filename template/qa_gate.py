#!/usr/bin/env python3
"""Sovereign Mesh QA gate — proves every page is genuinely useful and distinct.

Usage:
  qa_gate.py --dir ./pages/cluster-x/        # local HTML files
  qa_gate.py --urls urls.txt --base https://mesh.iamgodiam.net

Fails (exit 1) when any page violates the distinctiveness / SEO contract.
Thresholds live in QA_RULES below — versioned, append-only changes.
"""
import argparse, json, re, sys, urllib.request

QA_RULES = {
    "version": 3,
    "min_body_words": 300,
    "max_pairwise_jaccard": 0.55,   # body-text similarity ceiling between any two pages
    "min_internal_links": 3,
    "require_hub_link": True,        # every leaf must link its cluster hub
    "require_jsonld": ["FAQPage", "BreadcrumbList"],  # at least one of these types
    "max_title_len": 70,
    "min_desc_len": 50,
}

BOILERPLATE_TAGS = ["nav", "header", "footer"]

def strip_boilerplate(h):
    h = re.sub(r"<script.*?</script>", "", h, flags=re.S | re.I)
    h = re.sub(r"<style.*?</style>", "", h, flags=re.S | re.I)
    for tag in BOILERPLATE_TAGS:
        h = re.sub(r"<%s.*?</%s>" % (tag, tag), "", h, flags=re.S | re.I)
    return h

def body_text(h):
    t = re.sub(r"<[^>]+>", " ", strip_boilerplate(h))
    return re.sub(r"\s+", " ", t).strip()

def words(t):
    return [w.lower() for w in re.findall(r"[a-zA-Z']{2,}", t)]

def jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 1.0

def meta(h, name):
    m = re.search(r'<meta[^>]+name=["\']%s["\'][^>]+content=["\']([^"\']+)' % name, h, re.I)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']%s["\']' % name, h, re.I)
    return m.group(1).strip() if m else ""

def analyze(name, html):
    body = body_text(html)
    w = words(body)
    title = (re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I) or [None, ""])[1]
    title = re.sub(r"\s+", " ", title).strip()
    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    h1 = re.sub(r"<[^>]+>", "", h1s[0]).strip() if h1s else ""
    links = re.findall(r'href="([^"#]+?)"', html)
    internal = [l for l in links if not re.match(r"(?i)^(https?://(?!([a-z0-9-]+\.)?iamgodiam\.net)|mailto:|tel:|javascript:|data:)", l)]
    ld_types = set(re.findall(r'"@type"\s*:\s*"([^"]+)"', html))
    canonical = bool(re.search(r'rel=["\']canonical["\']', html, re.I))
    noindex = bool(re.search(r'content=["\'][^"\']*noindex', html, re.I))
    return {
        "name": name, "title": title, "h1": h1,
        "desc": meta(html, "description"),
        "body_words": len(w), "word_set": set(w),
        "internal_links": len(set(internal)),
        "hub_link": any("cluster-" in l for l in internal),
        "ld_types": sorted(ld_types), "canonical": canonical, "noindex": noindex,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", help="local directory of .html files")
    ap.add_argument("--urls", help="file with one path per line, fetched from --base")
    ap.add_argument("--base", default="https://mesh.iamgodiam.net")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    pages = {}
    if a.dir:
        import os
        for f in sorted(os.listdir(a.dir)):
            if f.endswith(".html"):
                pages[f] = open(os.path.join(a.dir, f), encoding="utf-8", errors="replace").read()
    elif a.urls:
        for line in open(a.urls):
            p = line.strip()
            if not p: continue
            url = a.base.rstrip("/") + "/" + p.lstrip("/")
            req = urllib.request.Request(url, headers={"User-Agent": "mesh-qa-gate"})
            pages[p] = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    else:
        ap.error("need --dir or --urls")

    analyzed = [analyze(n, h) for n, h in pages.items()]
    failures = []

    def fail(page, rule, detail):
        failures.append({"page": page, "rule": rule, "detail": detail})

    titles, descs, h1s = {}, {}, {}
    for pg in analyzed:
        if pg["body_words"] < QA_RULES["min_body_words"]:
            fail(pg["name"], "min_body_words", f"{pg['body_words']} < {QA_RULES['min_body_words']}")
        if not pg["title"]:
            fail(pg["name"], "title_missing", "no <title>")
        elif len(pg["title"]) > QA_RULES["max_title_len"]:
            fail(pg["name"], "title_too_long", f"{len(pg['title'])} chars")
        if len(pg["desc"]) < QA_RULES["min_desc_len"]:
            fail(pg["name"], "desc_missing_short", f"{len(pg['desc'])} chars")
        if not pg["h1"]:
            fail(pg["name"], "h1_missing", "no <h1>")
        if not pg["canonical"]:
            fail(pg["name"], "canonical_missing", "no canonical link")
        if pg["noindex"]:
            fail(pg["name"], "noindex_present", "page carries noindex")
        if not any(t in pg["ld_types"] for t in QA_RULES["require_jsonld"]):
            fail(pg["name"], "jsonld_missing", f"need one of {QA_RULES['require_jsonld']}, have {pg['ld_types']}")
        if pg["internal_links"] < QA_RULES["min_internal_links"]:
            fail(pg["name"], "internal_links", f"{pg['internal_links']} < {QA_RULES['min_internal_links']}")
        if QA_RULES["require_hub_link"] and not pg["hub_link"]:
            fail(pg["name"], "hub_link_missing", "no link to a cluster hub page")
        for key, store in (("title", titles), ("desc", descs), ("h1", h1s)):
            v = pg[{"title": "title", "desc": "desc", "h1": "h1"}[key]]
            if v:
                store.setdefault(v, []).append(pg["name"])
    for label, store in (("duplicate_title", titles), ("duplicate_desc", descs), ("duplicate_h1", h1s)):
        for v, owners in store.items():
            if len(owners) > 1:
                fail(", ".join(owners), label, f"{len(owners)} pages share: {v[:80]}")

    worst = (0, None, None)
    for i in range(len(analyzed)):
        for j in range(i + 1, len(analyzed)):
            s = jaccard(analyzed[i]["word_set"], analyzed[j]["word_set"])
            if s > worst[0]:
                worst = (s, analyzed[i]["name"], analyzed[j]["name"])
            if s > QA_RULES["max_pairwise_jaccard"]:
                fail(f"{analyzed[i]['name']} <> {analyzed[j]['name']}",
                     "near_duplicate", f"body Jaccard {s:.3f} > {QA_RULES['max_pairwise_jaccard']}")

    report = {
        "rules_version": QA_RULES["version"],
        "pages": len(analyzed),
        "failures": len(failures),
        "worst_pairwise_jaccard": round(worst[0], 3),
        "worst_pair": [worst[1], worst[2]],
        "details": failures[:50],
        "pass": not failures,
    }
    if a.json:
        print(json.dumps(report, indent=1))
    else:
        print(f"pages={report['pages']} failures={report['failures']} worst_jaccard={report['worst_pairwise_jaccard']} {report['worst_pair']}")
        for f in failures[:25]:
            print(f"  FAIL [{f['rule']}] {f['page']}: {f['detail']}")
        print("PASS" if report["pass"] else "FAIL")
    sys.exit(0 if report["pass"] else 1)

if __name__ == "__main__":
    main()
