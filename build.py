#!/usr/bin/env python3
"""
Bouwt de website van De Dissident uit content/site.json en de magazine-PDF's.

    python3 build.py            # bouwt site/
    python3 build.py --no-text  # slaat het uitlezen van de PDF's over (snel)

Artikelteksten worden uit de PDF's gelezen en gecachet in content/cache/.
Verwijder die map om opnieuw te laten uitlezen.
"""
import json
import os
import re
import shutil
import sys
import unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
DESKTOP = os.path.dirname(ROOT)
CONTENT = os.path.join(ROOT, "content")
CACHE = os.path.join(CONTENT, "cache")
STATIC = os.path.join(ROOT, "static")
OUT = os.path.join(ROOT, "site")

sys.path.insert(0, os.path.join(ROOT, "lib"))

# ---------------------------------------------------------------- helpers


def slugify(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "artikel"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ---------------------------------------------------------------- text sourcing


def article_text(edition, art, sources):
    """Return a list of paragraphs for one article, cached on disk."""
    key = f"{edition['id']}-p{art['page']}"
    cache_file = os.path.join(CACHE, key + ".json")
    if os.path.exists(cache_file):
        return json.load(open(cache_file))["paras"]

    paras = []
    spec = art.get("text")
    if spec and spec.startswith("pages:"):
        paras = _from_pages(spec[len("pages:"):])
    elif edition.get("pdf"):
        paras = _from_pdf(sources[edition["pdf"]], art["page"], art["end"])

    os.makedirs(CACHE, exist_ok=True)
    json.dump({"paras": paras}, open(cache_file, "w"), ensure_ascii=False, indent=1)
    return paras


def _from_pdf(rel_path, start, end):
    try:
        from pypdf import PdfReader
        import reflow
    except ImportError:
        return []
    path = os.path.join(DESKTOP, rel_path)
    if not os.path.exists(path):
        return []
    reader = PdfReader(path)
    if end is None:
        end = len(reader.pages)
    paras = []
    for n in range(start, min(end, len(reader.pages)) + 1):
        page = reader.pages[n - 1]
        try:
            layout = page.extract_text(extraction_mode="layout")
        except Exception:
            continue
        try:
            plain = page.extract_text()
        except Exception:
            plain = None
        for p in reflow.page_paragraphs(layout, plain):
            if reflow.is_body(p):
                paras.append(p)
    return dedupe(paras)


def _from_pages(rel_name):
    """Pull the prose out of an Apple Pages document."""
    try:
        import zipfile
        from iwa import iwa_chunks, readable_strings
    except ImportError:
        return []
    for base in (os.path.join(DESKTOP, "DD blad", "7"), DESKTOP):
        path = os.path.join(base, rel_name)
        if os.path.exists(path):
            break
    else:
        return []

    z = zipfile.ZipFile(path)
    chunks = []
    for name in z.namelist():
        if name.endswith(".iwa") and "Document" in name:
            for payload in iwa_chunks(z.read(name)):
                chunks.extend(readable_strings(payload, 40))

    paras = []
    for s in chunks:
        for line in s.split("\n"):
            line = re.sub(r"\s+", " ", line).strip()
            if len(line.split()) >= 12 and re.search(r"[a-z]{3,}\s+[a-z]{2,}", line):
                paras.append(line)
    return dedupe(paras)


def dedupe(paras):
    seen = set()
    out = []
    for p in paras:
        k = p[:80]
        if k in seen:
            continue
        seen.add(k)
        out.append(p)
    return out


# ---------------------------------------------------------------- images

IMG_EXT = (".jpg", ".jpeg", ".png")


def find_image(edition, art):
    """Locate the best source image for an article and copy it into site/sources."""
    name = art.get("image")
    if not name:
        return None

    # "site:foo.jpg" pulls a real photograph out of Bob's own site folder;
    # the edition-7 voorvertoning PNGs are scans of printed spreads, not photos.
    if name.startswith("site:"):
        src = os.path.join(DESKTOP, "DD site", "sources", name[len("site:"):])
        if os.path.exists(src):
            return copy_image(src, f"{edition['id']}-{slugify(art['title'])}")
        return None

    if edition["id"] == "ed7":
        src = os.path.join(DESKTOP, "DD blad", "7", "voorvertoning", name)
        if os.path.exists(src):
            return copy_image(src, f"{edition['id']}-{slugify(art['title'])}")
        return None

    if edition["id"] == "ed6":
        folder = os.path.join(DESKTOP, "DD blad", "6", "Links", name)
        if os.path.isdir(folder):
            best, best_size = None, 0
            for f in os.listdir(folder):
                if f.lower().endswith(IMG_EXT) and not f.startswith("."):
                    size = os.path.getsize(os.path.join(folder, f))
                    if size > best_size:
                        best, best_size = os.path.join(folder, f), size
            if best:
                return copy_image(best, f"{edition['id']}-{slugify(art['title'])}")
    return None


# Card thumbnails and article heroes need very different pixel counts; emitting
# both keeps the pages light without softening the large view.
IMAGE_WIDTHS = {"card": 800, "hero": 1600}


def copy_image(src, stem):
    """Write a card-sized and a hero-sized JPEG, and return their paths."""
    os.makedirs(os.path.join(OUT, "sources"), exist_ok=True)
    out = {}
    for label, width in IMAGE_WIDTHS.items():
        dest_name = f"{stem}-{width}.jpg"
        dest = os.path.join(OUT, "sources", dest_name)
        if not os.path.exists(dest):
            rc = os.system(
                f'sips -s format jpeg -s formatOptions 72 -Z {width} '
                f'"{src}" --out "{dest}" >/dev/null 2>&1')
            if rc != 0 or not os.path.exists(dest):
                shutil.copyfile(src, dest)
        out[label] = "sources/" + dest_name
    return out


# ---------------------------------------------------------------- page chrome


def head(title, css, description="", og_type="website"):
    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="theme-color" content="#173746">
<meta property="og:site_name" content="De Dissident">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23173746'/%3E%3Ctext x='16' y='24' font-family='Georgia,serif' font-size='22' font-weight='bold' fill='%23fff' text-anchor='middle'%3ED%3C/text%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Roboto+Condensed:ital,wght@0,400;0,600;0,700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css}">
</head>
<body>
<a class="skip-link" href="#inhoud">Naar de inhoud</a>
"""


def masthead(prefix, latest):
    return f"""<header class="masthead">
  <div class="masthead-top">
    <a class="wordmark" href="{prefix}index.html">Dissident</a>
    <div class="masthead-meta">
      <span class="issue-tag">{latest['number']}<sup>e</sup> editie</span>
      <span class="issue-date">{esc(latest['date_label'])}</span>
    </div>
  </div>
  <p class="tagline">Jongerenorganisatie Forum voor Democratie</p>
  <nav>
    <div class="nav-links">
      <a href="{prefix}index.html">Home</a>
      <a href="{prefix}archief.html">Archief</a>
      <div class="dropdown">
        <button type="button" class="nav-toggle" aria-expanded="false" aria-controls="rubrieken-menu">Rubrieken</button>
        <div class="dropdown-menu" id="rubrieken-menu" hidden></div>
      </div>
    </div>
    <noscript><p class="noscript-note">Zoeken en rubrieken werken alleen met JavaScript. Het <a href="{prefix}archief.html">archief</a> werkt zonder.</p></noscript>
    <form class="search" role="search" onsubmit="return false;">
      <input type="search" id="q" placeholder="Zoeken…" aria-label="Zoek artikelen"
             autocomplete="off" role="combobox" aria-expanded="false"
             aria-controls="search-results" aria-describedby="search-status">
      <span class="search-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      </span>
      <p class="visually-hidden" id="search-status" role="status" aria-live="polite"></p>
      <div class="search-results" id="search-results" role="listbox"
           aria-label="Zoekresultaten" hidden></div>
    </form>
  </nav>
</header>
"""


def footer(prefix):
    return f"""<footer>
  <img class="footer-mark" src="{prefix}sources/jfvd-logo.svg" alt="" width="32" height="32">
  <p>De Dissident — Jongerenorganisatie Forum voor Democratie</p>
</footer>
<script src="{prefix}search.js" defer></script>
</body>
</html>
"""


# ---------------------------------------------------------------- components


def card(a, prefix, featured=False):
    href = prefix + a["url"]
    img = a.get("img")
    media = (f'<div class="card-media"><img src="{prefix}{img["card"]}" alt="" '
             f'loading="lazy" decoding="async" width="800" height="600"></div>'
             if img else
             f'<div class="card-media card-media--tint {a["tint"]}">'
             f'<span class="folio" aria-hidden="true">{a["page"]}</span></div>')
    sub = f'<p>{esc(a["subtitle"])}</p>' if a.get("subtitle") else ""
    cls = "card card--featured" if featured else "card"
    return f"""<a class="{cls}" href="{href}" data-category="{esc(a['category'])}">
  <div class="bar"><span class="category">{esc(a['category'])}</span><span class="issue">Editie {a['edition_number']:02d}</span></div>
  {media}
  <h3>{esc(a['title'])}</h3>
  {sub}
  <span class="author">{esc(a['author'])}</span>
</a>"""


TINTS = ["navy", "blush", "teal"]


# ---------------------------------------------------------------- build


def build(read_text=True):
    data = json.load(open(os.path.join(CONTENT, "site.json")))
    sources = data["site"]["sources"]
    editions = sorted(data["editions"], key=lambda e: e["number"], reverse=True)
    latest = editions[0]

    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "artikel"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "sources"), exist_ok=True)

    # assets
    for f in os.listdir(STATIC):
        src = os.path.join(STATIC, f)
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(OUT, f))
    local_sources = os.path.join(ROOT, "sources")
    if os.path.isdir(local_sources):
        for f in os.listdir(local_sources):
            if not f.startswith("."):
                shutil.copyfile(os.path.join(local_sources, f),
                                os.path.join(OUT, "sources", f))

    # An article runs until the page before the next one starts, unless the
    # content file pins an explicit end page.
    for ed in editions:
        arts = ed["articles"]
        for i, art in enumerate(arts):
            if "end" not in art:
                art["end"] = arts[i + 1]["page"] - 1 if i + 1 < len(arts) else None

    # collect articles
    all_articles = []
    for ed in editions:
        for i, art in enumerate(ed["articles"]):
            slug = f"{ed['number']}-{slugify(art['title'])}"
            paras = article_text(ed, art, sources) if read_text else []
            rec = {
                "slug": slug,
                "url": f"artikel/{slug}.html",
                "title": art["title"],
                "subtitle": art.get("subtitle", ""),
                "category": art.get("category", "Artikel"),
                "author": art.get("author", "De Dissident"),
                "page": art["page"],
                "note": art.get("note", ""),
                "edition_id": ed["id"],
                "edition_number": ed["number"],
                "edition_label": ed["date_label"],
                "edition_theme": ed.get("theme", ""),
                "date": ed["date"],
                "pdf": sources.get(ed.get("pdf")) if ed.get("pdf") else None,
                "paras": paras,
                "img": find_image(ed, art),
                "tint": TINTS[i % len(TINTS)],
            }
            all_articles.append(rec)

    for a in all_articles:
        write_article(a, latest)

    write_home(all_articles, editions, latest)
    write_archive(all_articles, editions, latest)
    write_404(latest)
    for ed in editions:
        write_edition(ed, [a for a in all_articles if a["edition_id"] == ed["id"]], latest)
    write_index_json(all_articles)

    n_text = sum(1 for a in all_articles if a["paras"])
    print(f"site/ gebouwd — {len(all_articles)} artikelen, {n_text} met volledige tekst, "
          f"{len(editions)} edities")


def write_article(a, latest):
    prefix = "../"
    body = "\n".join(f"<p>{esc(p)}</p>" for p in a["paras"])
    if not body:
        pdf_note = ""
        if a["pdf"]:
            pdf_note = (f'<p class="placeholder-note">De tekst van dit artikel is nog niet '
                        f'overgezet. Het staat op pagina {a["page"]} van de gedrukte editie.</p>')
        else:
            pdf_note = ('<p class="placeholder-note">De tekst van dit artikel is nog niet '
                        'overgezet.</p>')
        body = pdf_note

    note = f'<p class="editor-note">{esc(a["note"])}</p>' if a["note"] else ""
    hero = (f'<figure class="article-hero"><img src="{prefix}{a["img"]["hero"]}" '
            f'srcset="{prefix}{a["img"]["card"]} 800w, {prefix}{a["img"]["hero"]} 1600w" '
            f'sizes="(max-width: 800px) 100vw, 760px" '
            f'alt="{esc(a["title"])}" decoding="async"></figure>'
            if a["img"] else "")
    sub = f'<p class="standfirst">{esc(a["subtitle"])}</p>' if a["subtitle"] else ""

    html = head(f"{a['title']} — De Dissident", prefix + "style.css",
                a["subtitle"], og_type="article")
    html += masthead(prefix, latest)
    html += f"""<main class="article" id="inhoud">
  <div class="bar">
    <span class="category">{esc(a['category'])}</span>
    <span class="issue">Editie {a['edition_number']:02d}</span>
  </div>
  <h1>{esc(a['title'])}</h1>
  {sub}
  <p class="byline">Door <span class="author">{esc(a['author'])}</span>
     · <a href="{prefix}editie-{a['edition_number']}.html">{a['edition_number']}<sup>e</sup> editie</a>
     · {esc(a['edition_label'])} · pagina {a['page']}</p>
  {note}
  {hero}
  <div class="article-body">
    {body}
  </div>
  <p class="back"><a href="{prefix}editie-{a['edition_number']}.html">← Alles uit de {a['edition_number']}<sup>e</sup> editie</a></p>
</main>
"""
    html += footer(prefix)
    open(os.path.join(OUT, "artikel", a["slug"] + ".html"), "w").write(html)


def write_home(articles, editions, latest):
    newest = [a for a in articles if a["edition_id"] == latest["id"]]
    rest = [a for a in articles if a["edition_id"] != latest["id"]]

    lead, others = newest[0], newest[1:]
    theme = f" — {latest['theme']}" if latest.get("theme") else ""

    html = head("De Dissident", "style.css",
                "Het tijdschrift van de Jongerenorganisatie Forum voor Democratie.")
    html += masthead("", latest)
    html += ('<main id="inhoud">\n'
             '<h1 class="visually-hidden">De Dissident — het tijdschrift van de JFVD</h1>\n')

    # lead article
    lead_media = (f'<div class="hero-media">'
                  f'<img src="{lead["img"]["hero"]}" '
                  f'srcset="{lead["img"]["card"]} 800w, {lead["img"]["hero"]} 1600w" '
                  f'sizes="(max-width: 900px) 100vw, 560px" '
                  f'alt="{esc(lead["title"])}" fetchpriority="high" decoding="async">'
                  f'<span class="square red" aria-hidden="true"></span></div>'
                  if lead["img"] else
                  '<div class="hero-media hero-media--tint">'
                  '<span class="square red" aria-hidden="true"></span></div>')
    html += f"""<a class="hero" href="{lead['url']}">
  {lead_media}
  <div class="hero-text">
    <div class="bar"><span class="category">Uitgelicht — {esc(lead['category'])}</span>
      <span class="issue">Editie {lead['edition_number']:02d}</span></div>
    <h2 class="hero-title">{esc(lead['title'])}</h2>
    <p>{esc(lead['subtitle'])}</p>
    <span class="author">{esc(lead['author'])}</span>
  </div>
</a>
"""

    html += f"""<section class="section-heading">
  <h2>Uit de {latest['number']}<sup>e</sup> editie{esc(theme)}</h2>
  <div class="rule"></div>
  <a class="section-link" href="editie-{latest['number']}.html">Hele editie</a>
</section>
<div class="grid" id="grid-latest">
{chr(10).join(card(a, "") for a in others)}
</div>
"""

    html += """<section class="section-heading">
  <h2>Uit het archief</h2>
  <div class="rule"></div>
  <a class="section-link" href="archief.html">Alle edities</a>
</section>
<div class="grid">
"""
    html += "\n".join(card(a, "") for a in rest[:6])
    html += "\n</div>\n</main>\n"
    html += footer("")
    open(os.path.join(OUT, "index.html"), "w").write(html)


def write_archive(articles, editions, latest):
    html = head("Archief — De Dissident", "style.css", "Alle edities van De Dissident.")
    html += masthead("", latest)
    html += '<main id="inhoud">\n<h1 class="page-title">Archief</h1>\n'
    html += '<p class="page-intro">Elke editie van De Dissident, met alle artikelen.</p>\n'

    for ed in editions:
        arts = [a for a in articles if a["edition_id"] == ed["id"]]
        theme = f" — {ed['theme']}" if ed.get("theme") else ""
        html += f"""<section class="section-heading">
  <h2>{ed['number']}<sup>e</sup> editie{esc(theme)}</h2>
  <div class="rule"></div>
  <a class="section-link" href="editie-{ed['number']}.html">{esc(ed['date_label'])}</a>
</section>
<ul class="toc">
"""
        for a in arts:
            sub = f' <span class="toc-sub">{esc(a["subtitle"])}</span>' if a["subtitle"] else ""
            html += (f'<li><span class="toc-page">{a["page"]}</span>'
                     f'<a href="{a["url"]}">{esc(a["title"])}</a>{sub}'
                     f'<span class="toc-author">{esc(a["author"])}</span></li>\n')
        html += "</ul>\n"

    html += "</main>\n" + footer("")
    open(os.path.join(OUT, "archief.html"), "w").write(html)


def write_edition(ed, arts, latest):
    theme = f" — {ed['theme']}" if ed.get("theme") else ""
    html = head(f"{ed['number']}e editie — De Dissident", "style.css")
    html += masthead("", latest)
    html += f"""<main id="inhoud">
<h1 class="page-title">{ed['number']}<sup>e</sup> editie{esc(theme)}</h1>
<p class="page-intro">{esc(ed['date_label'])} · {len(arts)} artikelen</p>
<div class="grid">
{chr(10).join(card(a, "") for a in arts)}
</div>
</main>
"""
    html += footer("")
    open(os.path.join(OUT, f"editie-{ed['number']}.html"), "w").write(html)


def write_404(latest):
    html = head("Pagina niet gevonden — De Dissident", "style.css")
    html += masthead("", latest)
    html += """<main id="inhoud">
<h1 class="page-title">Deze pagina bestaat niet</h1>
<p class="page-intro">Misschien is het artikel verplaatst of de link verouderd.</p>
<p class="back"><a href="index.html">← Naar de voorpagina</a> &nbsp;·&nbsp;
   <a href="archief.html">Blader door het archief</a></p>
</main>
"""
    html += footer("")
    open(os.path.join(OUT, "404.html"), "w").write(html)


def write_index_json(articles):
    idx = [{
        "t": a["title"], "s": a["subtitle"], "c": a["category"], "a": a["author"],
        "e": a["edition_number"], "u": a["url"], "p": a["page"],
        "x": " ".join(a["paras"])[:1200],
    } for a in articles]
    payload = json.dumps(idx, ensure_ascii=False, separators=(",", ":"))
    json.dump(idx, open(os.path.join(OUT, "search-index.json"), "w"), ensure_ascii=False)
    # Also emit the index as a script: browsers block fetch() over file://, so
    # opening site/index.html straight from Finder would otherwise kill search.
    with open(os.path.join(OUT, "search-index.js"), "w") as f:
        f.write("window.DD_INDEX=" + payload + ";\n")


if __name__ == "__main__":
    build(read_text="--no-text" not in sys.argv)
