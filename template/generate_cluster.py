#!/usr/bin/env python3
"""Sovereign Mesh page generator — the replicable template as code.

Input:  a cluster spec JSON (see pilot-cluster.json for the schema).
Output: one HTML file per page + the cluster hub, all passing qa_gate.py.

Page contract (enforced by qa_gate.py):
- H1 = one canonical question; direct answer in the first 100-150 words
- 300+ words of genuinely distinct body copy grounded in cited sources
- unique <title> / meta description / canonical
- FAQPage + BreadcrumbList JSON-LD
- links: up to the hub, sideways to siblings, out to the corpus anchor
- visible freshness date
"""
import json, sys, html, datetime

SITE = "https://mesh.iamgodiam.net"
CORPUS_BOOK = "https://iamgodiam.net/book"

CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{background:#070710;color:#e8d5a3;font-family:Georgia,serif;line-height:1.8;min-height:100vh}
a{color:#c9a84c;text-decoration:none}a:hover{text-decoration:underline}
main{max-width:760px;margin:0 auto;padding:3rem 1.5rem}
h1{font-size:2rem;margin-bottom:.5rem;color:#f5e7c1}
.answer-lede{font-size:1.15rem;border-left:3px solid #c9a84c;padding-left:1rem;margin:1.5rem 0;color:#f0e2b8}
h2{margin:2rem 0 .75rem;color:#f5e7c1;font-size:1.35rem}
.meta{color:#8a7a55;font-size:.85rem;margin-bottom:1rem}
nav.crumb{font-size:.85rem;color:#8a7a55;margin-bottom:2rem}
.corpus{background:#0d0d1a;border:1px solid #3a2a5a;border-radius:8px;padding:1rem 1.25rem;margin:1.5rem 0}
.corpus cite{display:block;color:#8a7a55;font-size:.85rem;margin-top:.5rem;font-style:normal}
footer{margin-top:3rem;padding-top:1.5rem;border-top:1px solid #2a2a4a;color:#8a7a55;font-size:.85rem}"""

def faq_jsonld(page, cluster):
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "FAQPage", "mainEntity": [{
                "@type": "Question", "name": page["question"],
                "acceptedAnswer": {"@type": "Answer", "text": page["answer"]}}]},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "IAMGODIAM Knowledge Mesh", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": cluster["title"], "item": f"{SITE}/pages/{cluster['hub']}"},
                {"@type": "ListItem", "position": 3, "name": page["question"]}]},
        ]}

def hub_jsonld(cluster):
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage", "name": cluster["title"], "description": cluster["description"]},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "IAMGODIAM Knowledge Mesh", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": cluster["title"]}]},
        ]}

def render_page(page, cluster, today):
    q = page["question"]
    stitle = page.get("stitle", q)
    title = f"{stitle} | IAMGODIAM"
    desc = page["answer"][:155]
    url = f"{SITE}/pages/{page['slug']}"
    hub_url = f"{SITE}/pages/{cluster['hub']}"
    sib_links = "\n".join(
        f'<li><a href="{s["slug"]}">{html.escape(s["question"])}</a></li>'
        for s in page.get("siblings", []))
    corpus = "\n".join(
        f'''<div class="corpus"><p>&ldquo;{html.escape(c["quote"])}&rdquo;</p><cite>Abba Talk corpus &middot; <a href="{CORPUS_BOOK}">{html.escape(c["ref"])}</a> &middot; <a href="https://iamgodiam.net/api/passage?id={c["pid"]}">read the passage</a></cite></div>'''
        for c in page.get("corpus", []))
    sections = "\n".join(f"<h2>{html.escape(s['h'])}</h2>\n<p>{s['body_html']}</p>"
                         for s in page.get("sections", []))
    ld = json.dumps(faq_jsonld(page, cluster), ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{url}">
<script type="application/ld+json">{ld}</script>
<style>{CSS}</style>
</head>
<body>
<main>
<nav class="crumb"><a href="/">Mesh</a> &rsaquo; <a href="{cluster['hub']}">{html.escape(cluster["title"])}</a> &rsaquo; {html.escape(q[:60])}</nav>
<h1>{html.escape(q)}</h1>
<p class="meta">IAMGODIAM Knowledge Mesh &middot; {html.escape(cluster["title"])} &middot; reviewed {today}</p>
<p class="answer-lede">{page["answer_html"]}</p>
{corpus}
{sections}
<h2>Keep exploring</h2>
<ul>
<li><a href="{cluster['hub']}">{html.escape(cluster["title"])} — cluster hub</a></li>
{sib_links}
<li><a href="{CORPUS_BOOK}">Abba Talk — Speak with the Father's House</a></li>
</ul>
</main>
<footer><p><a href="/">IAMGODIAM — Sovereign Knowledge Mesh</a> &middot; Black-first, agentic-generated, blockchain-anchored.</p></footer>
</body>
</html>
"""

def render_hub(cluster, today):
    page_links = "\n".join(
        f'<li><a href="{p["slug"]}">{html.escape(p["question"])}</a><br><span style="color:#8a7a55;font-size:.9rem">{html.escape(p["answer"])}</span></li>'
        for p in cluster["pages"])
    ld = json.dumps(hub_jsonld(cluster), ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(cluster["title"])} — IAMGODIAM Knowledge Mesh</title>
<meta name="description" content="{html.escape(cluster["description"])}">
<link rel="canonical" href="{SITE}/pages/{cluster['hub']}">
<script type="application/ld+json">{ld}</script>
<style>{CSS}</style>
</head>
<body>
<main>
<nav class="crumb"><a href="/">Mesh</a> &rsaquo; {html.escape(cluster["title"])}</nav>
<h1>{html.escape(cluster["title"])}</h1>
<p class="meta">Knowledge cluster &middot; {len(cluster["pages"])} pages &middot; reviewed {today}</p>
<p class="answer-lede">{html.escape(cluster["description"])}</p>
<h2>How to read this cluster</h2>
<p>Each page takes one question and answers it three ways: first a direct answer you can read in a minute, then the words of the revelation itself &mdash; quoted verbatim from the 30,316-passage Abba Talk corpus, with links so you can read every passage in full &mdash; then a study commentary written through a Black-first lens, connecting the text to the lived work of justice and liberation. The questions build on each other, but each page stands alone. Start anywhere; follow the links sideways when a question opens another.</p>
<h2>Pages in this cluster</h2>
<ul>{page_links}</ul>
<p><a href="/">Return to the Mesh home</a> &middot; <a href="https://iamgodiam.net/book">Abba Talk — the Book</a></p>
</main>
<footer><p><a href="/">IAMGODIAM — Sovereign Knowledge Mesh</a></p></footer>
</body>
</html>
"""

def main():
    spec_path, out_dir = sys.argv[1], sys.argv[2]
    import os
    spec = json.load(open(spec_path))
    cluster = spec["cluster"]
    today = datetime.date.today().isoformat()
    os.makedirs(out_dir, exist_ok=True)
    # wire siblings automatically
    for i, p in enumerate(cluster["pages"]):
        p["siblings"] = [s for j, s in enumerate(cluster["pages"]) if j != i][:4]
    for p in cluster["pages"]:
        open(os.path.join(out_dir, p["slug"]), "w").write(render_page(p, cluster, today))
    open(os.path.join(out_dir, cluster["hub"]), "w").write(render_hub(cluster, today))
    print(f"wrote {len(cluster['pages'])} pages + hub -> {out_dir}")

if __name__ == "__main__":
    main()
