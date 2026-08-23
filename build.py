#!/usr/bin/env python3
"""
Bouwt de website van De Dissident uit content/site.json en content/tekst/.

    python3 build.py

Leest zelf geen PDF's. De artikelteksten in content/tekst/ worden apart en
eenmalig aangemaakt met tools/extract_text.py, wanneer er een nieuwe editie is.
"""
import json
import os
import re
import shutil
import sys
import unicodedata
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
DESKTOP = os.path.dirname(ROOT)
CONTENT = os.path.join(ROOT, "content")
TEKST = os.path.join(CONTENT, "tekst")
STATIC = os.path.join(ROOT, "static")
OUT = os.path.join(ROOT, "site")

# Gevuld in build() uit content/site.json.
SITE = {}
EDITIONS = []

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


def article_text(edition, art):
    """Alinea's van één artikel, zoals tools/extract_text.py ze heeft opgeslagen."""
    if not art.get("page"):
        return []
    path = os.path.join(TEKST, f"{edition['id']}-p{art['page']}.json")
    if not os.path.exists(path):
        return []
    return json.load(open(path))["paras"]


# ---------------------------------------------------------------- images

IMG_EXT = (".jpg", ".jpeg", ".png")


# Elke editie bewaart haar beeldmateriaal in een eigen map, met per artikel
# een submap. "image" in site.json is de naam van die submap.
ART_FOLDERS = {
    "ed7": os.path.join("DD blad", "7", "bronnen"),
    "ed6": os.path.join("DD blad", "6", "Links"),
}


def find_image(edition, art):
    """Locate the best source image for an article and copy it into site/sources."""
    name = art.get("image")
    if not name:
        return None

    stem = f"{edition['id']}-{slugify(art['title'])}"

    base = ART_FOLDERS.get(edition["id"])
    if not base:
        return None

    src = os.path.join(DESKTOP, base, name)
    if os.path.isfile(src):
        return copy_image(src, stem)

    if os.path.isdir(src):
        best, best_size = None, 0
        for f in os.listdir(src):
            if f.lower().endswith(IMG_EXT) and not f.startswith("."):
                size = os.path.getsize(os.path.join(src, f))
                if size > best_size:
                    best, best_size = os.path.join(src, f), size
        if best:
            return copy_image(best, stem)
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


# ---------------------------------------------------------------- accent colours

# --accent-ink staat zowel op een wit vel (artikelpagina, popovers) als
# rechtstreeks op het iets donkerdere grijze canvas (rubrieken, labels). Tegen
# CANVAS kalibreren is de strengere eis en dekt PAPER automatisch mee.
PAPER = (0xFF, 0xFF, 0xFF)
CANVAS = (0xE7, 0xE4, 0xDE)
# De inktkleur van --on-canvas: iets lichter dan zuiver zwart, dus daar moet
# --accent-wash (de markeerstift-band) ook echt tegen gemeten worden.
INK = (0x1A, 0x17, 0x12)


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _luminance(rgb):
    def chan(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(rgb_a, rgb_b):
    la, lb = _luminance(rgb_a), _luminance(rgb_b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def readable_ink(accent, bg=CANVAS, target=4.5):
    """Darken an accent until it is legible as text on the page background.

    The printed accents are chosen for ink on paper: the amber, pink and yellow
    used in edition 7 sit around 2:1 against our cream, which is unreadable on
    screen. Keeping the hue and dropping the brightness preserves the identity
    of the colour while clearing the contrast bar. Calibrated against the grey
    canvas rather than pure white: that is the harder of the two backgrounds
    this colour appears on, so clearing it also clears the white article page
    and popovers."""
    r, g, b = _hex_to_rgb(accent)
    if contrast((r, g, b), bg) >= target:
        return accent
    for step in range(1, 101):
        f = 1 - step / 100
        cand = (round(r * f), round(g * f), round(b * f))
        if contrast(cand, bg) >= target:
            return "#%02x%02x%02x" % cand
    return "#000000"


def light_wash(accent, target=4.5):
    """Lighten an accent until dark ink stays readable on top of it.

    Used as the marker-highlighter band behind a headline: the ink stays dark
    grey/black (--on-canvas), so the colour underneath has to be light enough
    to read through. A saturated blue would swallow the letters."""
    r, g, b = _hex_to_rgb(accent)
    if contrast((r, g, b), INK) >= target:
        return accent
    for step in range(1, 101):
        f = step / 100
        cand = (round(r + (255 - r) * f),
                round(g + (255 - g) * f),
                round(b + (255 - b) * f))
        if contrast(cand, INK) >= target:
            return "#%02x%02x%02x" % cand
    return "#ffffff"


def deep_ink(accent, target=7.0):
    """Darken an accent until white text sits comfortably on top of it.

    Used where the accent becomes a filled panel rather than type. The printed
    yellows and ambers are near-white in luminance, so they need to come down a
    long way before they can carry a headline."""
    r, g, b = _hex_to_rgb(accent)
    white = (255, 255, 255)
    if contrast((r, g, b), white) >= target:
        return accent
    for step in range(1, 101):
        f = 1 - step / 100
        cand = (round(r * f), round(g * f), round(b * f))
        if contrast(cand, white) >= target:
            return "#%02x%02x%02x" % cand
    return "#000000"


def sheet_vars(accent):
    """De custom properties van een editievel als kale declaraties.

    Apart van sheet_style() omdat edition.js ze bij het wisselen rechtstreeks
    op het style-attribuut van .expo-row zet — daar past geen heel attribuut."""
    if not accent:
        return ""
    return (f"--accent: {accent}; --accent-ink: {readable_ink(accent)}; "
            f"--accent-deep: {deep_ink(accent)}; --accent-wash: {light_wash(accent)}")


def sheet_style(accent):
    """Custom properties voor een editievel.

    De hele main ligt als een gekleurd vel op de grijze pagina, dus het accent
    hoeft maar één keer gezet te worden: alles eronder erft het, inclusief het
    hero-paneel — dat vult zich met dezelfde --accent-deep."""
    vars_ = sheet_vars(accent)
    return f' style="{vars_}"' if vars_ else ""


def accent_style(accent):
    """De afgeleiden van een accentkleur, als inline custom properties.

    Elke rol vraagt een andere helderheid:
      --accent       de drukkleur zelf, voor lijnen en randen
      --accent-ink   donker genoeg als tekst op het lichte canvas of een wit vel
      --accent-deep  donker genoeg om witte tekst te dragen (hero, gekleurd vlak)
      --accent-wash  licht genoeg om donkere tekst te dragen (markeerstift)"""
    if not accent:
        return ""
    return (f' style="--accent: {accent}; --accent-ink: {readable_ink(accent)}; '
            f'--accent-deep: {deep_ink(accent)}; --accent-wash: {light_wash(accent)}"')


# ---------------------------------------------------------------- page chrome


def head(title, css, description="", og_type="website"):
    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="theme-color" content="#e7e4de">
<meta property="og:site_name" content="De Dissident">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%231a1712'/%3E%3Ctext x='16' y='24' font-family='Georgia,serif' font-size='22' font-weight='bold' fill='%23e7e4de' text-anchor='middle'%3ED%3C/text%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Playfair+Display:ital,wght@0,700;0,800;0,900;1,700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css}">
<noscript><style>
/* De load-in animaties wachten op reveal.js (.in-view); zonder JavaScript zou
   de pagina anders leeg blijven, dus dan meteen alles tonen. */
.reveal, .tw-word {{ opacity: 1 !important; transform: none !important; animation: none !important; }}
.tw-cursor {{ display: none; }}
</style></noscript>
</head>
<body>
<a class="skip-link" href="#inhoud">Naar de inhoud</a>
<div class="page-shell">
"""


def masthead(prefix):
    # De woorden krijgen blokjes ertussen, als op een krantenkop. De scheiding
    # is decoratief, dus schermlezers slaan hem over.
    sep = '<span class="dot" aria-hidden="true"></span>'
    tagline = sep.join(esc(w) for w in SITE.get("tagline", "").split())
    if tagline:
        tagline += (f'<img class="tagline-mark" src="{prefix}sources/jfvd-logo.svg" '
                    f'alt="" width="14" height="14">')
    return f"""<header class="masthead">
  <div class="masthead-brand">
    <a class="wordmark" href="{prefix}index.html">De Dissident</a>
    <p class="tagline">{tagline}</p>
  </div>
  <nav>
    <noscript><p class="noscript-note">Zoeken werkt alleen met JavaScript.</p></noscript>
    <form class="search" role="search" onsubmit="return false;">
      <span class="search-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      </span>
      <input type="search" id="q" placeholder="Zoeken…" aria-label="Zoek artikelen"
             autocomplete="off" role="combobox" aria-expanded="false"
             aria-controls="search-overlay" aria-describedby="search-status">
      <p class="visually-hidden" id="search-status" role="status" aria-live="polite"></p>
    </form>
  </nav>
</header>
<div class="search-overlay" id="search-overlay" role="dialog" aria-modal="true"
     aria-label="Zoeken in het archief" hidden>
  <div class="search-overlay-inner">
    <div class="search-overlay-head">
      <div class="search-overlay-field" id="search-overlay-field"></div>
      <button type="button" class="search-overlay-close" id="search-overlay-close"
              aria-label="Zoeken sluiten">&times;</button>
    </div>
    <p class="page-intro" id="search-overlay-intro">Alle edities van De Dissident, met alle artikelen.</p>
    <div id="search-overlay-results"></div>
  </div>
</div>
"""


def footer(prefix, scripts=()):
    extra = "".join(f'\n<script src="{prefix}{s}" defer></script>' for s in scripts)
    edities = "".join(
        f'<li><a href="{prefix}editie-{ed["number"]}.html">{ed["number"]}<sup>e</sup> editie</a></li>\n'
        for ed in sorted(EDITIONS, key=lambda e: e["number"]))
    jaar = date.today().year
    return f"""</div>
<footer>
  <div class="footer-inner">
    <div class="footer-cols">
      <div class="footer-col">
        <h2 class="footer-heading">Het tijdschrift</h2>
        <p class="footer-text">Het meest gewaagde jongerenblad van het Westen.</p>
      </div>
      <div class="footer-col">
        <h2 class="footer-heading">Edities</h2>
        <ul class="footer-editions">
{edities}        </ul>
      </div>
      <div class="footer-col">
        <h2 class="footer-heading">Meedoen</h2>
        <p class="footer-text"><a href="mailto:redactie@jongerenfvd.nl">Schrijf mee</a> —
           stuur je kopij naar <a href="mailto:redactie@jongerenfvd.nl">redactie@jongerenfvd.nl</a>.</p>
        <p class="footer-text"><a href="https://jfvd.nl" target="_blank" rel="noopener">jfvd.nl</a></p>
      </div>
    </div>
    <div class="footer-bottom">
      <a class="footer-jfvd" href="https://jfvd.nl" target="_blank" rel="noopener"
         aria-label="Naar de JFVD site">
        <span class="footer-jfvd-flip">
          <span class="footer-jfvd-face footer-jfvd-face--front" aria-hidden="true">
            <svg viewBox="0 0 70 70" focusable="false">
              <g transform="matrix(0.7,0,0,0.7,0,0)">
                <path fill="currentColor" d="M50,0C77.596,0 100,22.404 100,50C100,77.596 77.596,100 50,100C22.404,100 0,77.596 0,50C0,22.404 22.404,0 50,0ZM32.757,38.294L23.913,38.294L23.913,40.502L25.362,42.102L24.018,64.307L32.652,64.307L31.308,42.102L32.757,40.502L32.757,38.294ZM82.16,76.639L17.178,76.639L17.178,79.238L82.16,79.238L82.16,76.639ZM46.864,38.294L38.017,38.294L38.017,40.502L39.468,42.102L38.124,64.307L46.756,64.307L45.412,42.102L46.863,40.502L46.864,38.294ZM60.967,38.294L52.123,38.294L52.123,40.502L53.572,42.102L52.223,64.307L60.857,64.307L59.523,42.102L60.972,40.502L60.967,38.294ZM75.071,38.294L66.227,38.294L66.227,40.502L67.676,42.102L66.332,64.307L74.966,64.307L73.622,42.102L75.071,40.502L75.071,38.294ZM77.869,33.026L21.469,33.026L21.469,35.625L77.869,35.625L77.869,33.026ZM82.16,28.808L49.671,15.468L17.178,28.808L17.178,30.74L82.16,30.74L82.16,28.808ZM77.869,66.973L21.469,66.973L21.469,69.572L77.869,69.572L77.869,66.973ZM79.71,71.807L19.631,71.807L19.631,74.406L79.71,74.406L79.71,71.807Z"/>
              </g>
            </svg>
          </span>
          <span class="footer-jfvd-face footer-jfvd-face--back">Naar de JFVD site <span aria-hidden="true">↗</span></span>
        </span>
      </a>
      <p class="footer-copyright">© {jaar} — een uitgave van de Jongerenorganisatie Forum voor Democratie</p>
    </div>
  </div>
</footer>
<script src="{prefix}search.js" defer></script>
<script src="{prefix}footer.js" defer></script>{extra}
</body>
</html>
"""


# ---------------------------------------------------------------- components


def build():
    data = json.load(open(os.path.join(CONTENT, "site.json")))
    SITE.update(data["site"])
    editions = sorted(data["editions"], key=lambda e: e["number"], reverse=True)
    latest = editions[0]
    EDITIONS.clear()
    EDITIONS.extend(editions)

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

    # collect articles
    all_articles = []
    for ed in editions:
        for i, art in enumerate(ed["articles"]):
            slug = f"{ed['number']}-{slugify(art['title'])}"
            paras = article_text(ed, art)
            rec = {
                "slug": slug,
                "url": f"artikel/{slug}.html",
                "title": art["title"],
                "subtitle": art.get("subtitle", ""),
                "category": art.get("category", "Artikel"),
                "author": art.get("author", "De Dissident"),
                "page": art["page"],
                "note": art.get("note", ""),
                "accent": ed.get("accent"),
                "pullquotes": art.get("pullquotes", []),
                "edition_id": ed["id"],
                "edition_number": ed["number"],
                "edition_label": ed["date_label"],
                "edition_theme": ed.get("theme", ""),
                "date": ed["date"],
                "paras": paras,
                "img": find_image(ed, art),
            }
            all_articles.append(rec)

    for a in all_articles:
        write_article(a)

    write_home(all_articles, editions, latest)
    write_archive(all_articles, editions)
    write_404()
    for ed in editions:
        write_edition(ed, [a for a in all_articles if a["edition_id"] == ed["id"]], editions)
    write_editions_js(all_articles, editions, latest)
    write_index_json(all_articles, editions)

    n_text = sum(1 for a in all_articles if a["paras"])
    print(f"site/ gebouwd — {len(all_articles)} artikelen, {n_text} met volledige tekst, "
          f"{len(editions)} edities")


def _quote_key(s):
    """Whitespace- and punctuation-free key, for matching quotes to paragraphs."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def drop_quoted_paragraphs(paras, quotes, min_len=25):
    """Remove body paragraphs that a pull quote already carries.

    The quote is set in display type in the magazine, so the extractor picks it
    up as body text too — sometimes letter-spaced ("In Ne d e rl a n d"), which
    is why the comparison ignores spacing entirely."""
    keys = [_quote_key(q["text"]) for q in quotes]
    out = []
    for p in paras:
        k = _quote_key(p)
        if len(k) >= min_len and any(k in qk or qk in k for qk in keys):
            continue
        out.append(p)
    return out


def render_body(paras, quotes):
    """Weave the pull quotes through the paragraphs, evenly spaced.

    They are placed rather than positioned where the magazine had them: the
    print layout hangs them in a column, which has no equivalent here."""
    paras = drop_quoted_paragraphs(paras, quotes)
    blocks = [f"<p>{esc(p)}</p>" for p in paras]
    if not quotes or len(blocks) < 4:
        return "\n".join(blocks)

    out = []
    step = len(blocks) / (len(quotes) + 1)
    drops = {max(1, round(step * (i + 1))): q for i, q in enumerate(quotes)}
    for i, block in enumerate(blocks):
        q = drops.get(i)
        if q:
            bron = (f'<footer class="pullquote-source">{esc(q["source"])}</footer>'
                    if q.get("source") else "")
            out.append(f'<blockquote class="pullquote">'
                       f'<p>{esc(q["text"])}</p>{bron}</blockquote>')
        out.append(block)
    return "\n".join(out)


def write_article(a):
    prefix = "../"
    body = render_body(a["paras"], a.get("pullquotes") or [])
    if not body:
        body = ('<p class="placeholder-note">De tekst van dit artikel is nog niet '
                'overgezet.</p>')

    note = f'<p class="editor-note">{esc(a["note"])}</p>' if a["note"] else ""
    hero = (f'<figure class="article-hero"><img src="{prefix}{a["img"]["hero"]}" '
            f'srcset="{prefix}{a["img"]["card"]} 800w, {prefix}{a["img"]["hero"]} 1600w" '
            f'sizes="(max-width: 800px) 100vw, 760px" '
            f'alt="{esc(a["title"])}" decoding="async"></figure>'
            if a["img"] else "")
    sub = f'<p class="standfirst">{esc(a["subtitle"])}</p>' if a["subtitle"] else ""

    style = accent_style(a.get("accent"))
    cls = "article article--accent" if a.get("accent") else "article"

    html = head(f"{a['title']} — De Dissident", prefix + "style.css",
                a["subtitle"], og_type="article")
    html += masthead(prefix)
    html += f"""<main class="{cls}" id="inhoud"{style}>
  <div class="bar">
    <span class="category">{esc(a['category'])}</span>
    <span class="issue">Editie {a['edition_number']:02d}</span>
  </div>
  <h1>{esc(a['title'])}</h1>
  {sub}
  <p class="byline">Door <span class="author">{esc(a['author'])}</span>
     · <a href="{prefix}editie-{a['edition_number']}.html">{a['edition_number']}<sup>e</sup> editie</a>
     · {esc(a['edition_label'])}</p>
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


def edition_switch(editions, current, prefix=""):
    """Smalle strook met alle editienummers; de huidige is gemarkeerd."""
    items = []
    for ed in sorted(editions, key=lambda e: e["number"]):
        label = f"{ed['number']:02d}"
        if ed["id"] == current["id"]:
            items.append(f'<li><span class="is-current" aria-current="page">'
                         f'{label}</span></li>')
        else:
            items.append(f'<li><a href="{prefix}editie-{ed["number"]}.html" '
                         f'title="{esc(ed["date_label"])}">{label}</a></li>')
    theme = f" — {current['theme']}" if current.get("theme") else ""
    return f"""<nav class="edition-switch" aria-label="Kies een editie">
  <span class="edition-switch-label">Editie</span>
  <ul>{"".join(items)}</ul>
  <span class="edition-switch-meta">{esc(current['date_label'])}{esc(theme)}</span>
</nav>
"""


# ---------------------------------------------------------------- load-in

# Alleen de homepage animeert (zie animate= in write_home() versus
# write_edition()). Kaarten (hero, features, listings) schuiven na elkaar in;
# binnen elke kaart schuiven rubriek/kop/omschrijving/auteur/beeld op hun
# beurt. REVEAL_CARD_CAP voorkomt dat een editie met veel listings de laatste
# kaart pas na seconden laat verschijnen — daarna delen ze dezelfde vertraging.
REVEAL_CARD_STEP = 0.09
REVEAL_CARD_CAP = 8
REVEAL_ELEM_STEP = 0.055
REVEAL_DURATION = 0.5    # moet gelijk aan de animation-duration van .reveal


def _reveal(animate, card_i, elem_i, right=False):
    """(' class=...', ' style=...') fragmenten voor één load-in element, of
    ("", "") als animate False is. --d is de animation-delay; zie .reveal in
    style.css. De class-fragmenten zijn bedoeld om te plakken achter een
    bestaande klassenaam (class="hero-title{c}") — voor elementen zonder
    eigen basisklasse (kale <h3>/<p>) gebruik je _bare() hieronder."""
    if not animate:
        return "", ""
    card = min(card_i, REVEAL_CARD_CAP)
    d = card * REVEAL_CARD_STEP + elem_i * REVEAL_ELEM_STEP
    cls = " reveal reveal--right" if right else " reveal"
    return cls, f' style="--d:{d:.3f}s"'


def _bare(c, s):
    """class=/style=-attribuutfragment voor een element zonder eigen
    basisklasse: zonder animatie blijft het element helemaal kaal."""
    return (f' class="{c.strip()}"' if c else "") + s


def typewriter_html(text, start_delay):
    """Elk woord in een eigen span met oplopende --d: de lange voorwoordtekst
    "typt" zichzelf snel uit in plaats van in/uit te schuiven zoals de rest.
    Alleen woorden (niet losse letters) — dat houdt de pagina licht en laat
    tekst gewoon selecteerbaar/doorzoekbaar. Zie .tw-word in style.css."""
    words = esc(text).split(" ")
    spans = " ".join(
        f'<span class="tw-word" style="--d:{start_delay + i * 0.014:.3f}s">{w}</span>'
        for i, w in enumerate(words))
    cursor_delay = start_delay + len(words) * 0.014
    cursor = f'<span class="tw-cursor" aria-hidden="true" style="--d:{cursor_delay:.3f}s"></span>'
    return spans + cursor


def hero_block(lead, prefix="", animate=False, card_i=0):
    c0, s0 = _reveal(animate, card_i, 0)
    c1, s1 = _reveal(animate, card_i, 1)
    c2, s2 = _reveal(animate, card_i, 2)
    c3, s3 = _reveal(animate, card_i, 3, right=True)

    # Vierkante thumbnail die uit de rechteronderhoek van het blauwe vlak steekt:
    # zie .hero-media in style.css voor de offset-wiskunde.
    media = (f'<div class="hero-media{c3}"{s3}>'
             f'<img src="{prefix}{lead["img"]["hero"]}" '
             f'srcset="{prefix}{lead["img"]["card"]} 800w, {prefix}{lead["img"]["hero"]} 1600w" '
             f'sizes="(max-width: 900px) 50vw, 360px" '
             f'alt="{esc(lead["title"])}" fetchpriority="high" decoding="async">'
             f'</div>'
             if lead["img"] else "")

    return f"""<a class="hero" href="{prefix}{lead['url']}">
  <span class="hero-label">Uitgelicht</span>
  <h2 class="hero-title{c0}"{s0}>{esc(lead['title'])}</h2>
  <div class="hero-foot">
    <p class="hero-standfirst{c1}"{s1}>{esc(lead['subtitle'])}</p>
    <span class="author{c2}"{s2}>{esc(lead['author'])}</span>
  </div>
  {media}
</a>
"""


def _square_media(a, prefix, cls, class_extra="", style_extra=""):
    """Vierkante thumbnail, of een gekleurd vlak met lettermerk als beeld ontbreekt."""
    img = a.get("img")
    if img:
        return (f'<div class="{cls}{class_extra}"{style_extra}>'
                f'<img src="{prefix}{img["card"]}" alt="" '
                f'loading="lazy" decoding="async"></div>')
    return (f'<div class="{cls} {cls}--tint{class_extra}"{style_extra}>'
            f'<span class="lettermark" aria-hidden="true">D</span></div>')


def feature(a, prefix="", animate=False, card_i=0):
    """Kop plus korte omschrijving links, vierkant beeld rechts."""
    c0, s0 = _reveal(animate, card_i, 0)
    c1, s1 = _reveal(animate, card_i, 1)
    c2, s2 = _reveal(animate, card_i, 2)
    c3, s3 = _reveal(animate, card_i, 3)
    c4, s4 = _reveal(animate, card_i, 4, right=True)

    sub = f'<p{_bare(c2, s2)}>{esc(a["subtitle"])}</p>' if a.get("subtitle") else ""
    return f"""<a class="feature" href="{prefix}{a['url']}" data-category="{esc(a['category'])}">
  <div class="feature-text">
    <div class="bar"><span class="category{c0}"{s0}>{esc(a['category'])}</span></div>
    <h3{_bare(c1, s1)}><span class="mark">{esc(a['title'])}</span></h3>
    {sub}
    <span class="author{c3}"{s3}>{esc(a['author'])}</span>
  </div>
  {_square_media(a, prefix, "feature-media", c4, s4)}
</a>"""


def listing(a, prefix="", animate=False, card_i=0):
    """Alleen een kop links, klein vierkant beeld rechts."""
    c0, s0 = _reveal(animate, card_i, 0)
    c1, s1 = _reveal(animate, card_i, 1)
    c2, s2 = _reveal(animate, card_i, 2, right=True)

    return f"""<a class="listing" href="{prefix}{a['url']}" data-category="{esc(a['category'])}">
  <div class="listing-text">
    <span class="category{c0}"{s0}>{esc(a['category'])}</span>
    <h3{_bare(c1, s1)}><span class="mark">{esc(a['title'])}</span></h3>
  </div>
  {_square_media(a, prefix, "listing-media", c2, s2)}
</a>"""


def exposition(ed, arts, editions, prefix="", animate=False):
    """De expositie van één editie: hero, drie uitgelichte stukken, dan de rest."""
    if not arts:
        return "<p class=\"page-intro\">Deze editie heeft nog geen artikelen.</p>\n"

    lead, features, listings = arts[0], arts[1:4], arts[4:]
    html = edition_switch(editions, ed, prefix)
    html += hero_block(lead, prefix, animate, 0)
    if features:
        html += ('<div class="features">\n'
                 + "\n".join(feature(a, prefix, animate, 1 + i)
                             for i, a in enumerate(features))
                 + "\n</div>\n")
    if listings:
        base = 1 + len(features)
        html += ('<div class="listings">\n'
                 + "\n".join(listing(a, prefix, animate, base + i)
                             for i, a in enumerate(listings))
                 + "\n</div>\n")
    return html


def voorwoord_block(ed, animate=False):
    """Rechts op de grijze tafel: portret, naam van de hoofdredacteur, voorwoord.

    Alleen zichtbaar op brede schermen, naast het vel (zie .expo-row in de CSS).
    Zonder bekende auteur — bijvoorbeeld een editie die nog in opbouw is — blijft
    dit stukje helemaal weg in plaats van een leeg kader te tonen."""
    auteur = ed.get("voorwoord_auteur")
    if not auteur:
        return ""
    rol = ed.get("voorwoord_rol", "")
    tekst = ed.get("voorwoord")
    initialen = "".join(w[0] for w in auteur.split()[:2]).upper()

    # Eigen, korte cascade (card_i=0), los van de artikelkaarten ernaast: het
    # voorwoord mag meteen verschijnen, niet pas na een lange lijst listings.
    c0, s0 = _reveal(animate, 0, 0)
    c1, s1 = _reveal(animate, 0, 1)

    if tekst:
        # De lange tekst schuift niet in maar "typt" zichzelf, ná de byline.
        start = REVEAL_ELEM_STEP + REVEAL_DURATION if animate else 0
        body = f"<p>{typewriter_html(tekst, start) if animate else esc(tekst)}</p>"
    else:
        c2, s2 = _reveal(animate, 0, 2)
        body = (f'<p class="placeholder-note{c2}"{s2}>Het voorwoord van deze editie '
                f'is nog niet overgezet.</p>')

    return f"""<aside class="voorwoord-kolom">
  <div class="voorwoord-portret{c0}" aria-hidden="true"{s0}><span>{esc(initialen)}</span></div>
  <p class="voorwoord-byline{c1}"{s1}>{esc(auteur)}<span>{esc(rol)}</span></p>
  {body}
</aside>
"""


HOME_TITLE = "De Dissident"


def write_home(articles, editions, latest):
    arts = [a for a in articles if a["edition_id"] == latest["id"]]
    html = head(HOME_TITLE, "style.css",
                "Het tijdschrift van de Jongerenorganisatie Forum voor Democratie.")
    html += masthead("")
    html += f'<div class="expo-row"{sheet_style(latest.get("accent"))}>\n'
    html += ('<main id="inhoud" class="expo">\n'
             '<h1 class="visually-hidden">De Dissident — het tijdschrift van de JFVD</h1>\n')
    html += exposition(latest, arts, editions, animate=True)
    html += "</main>\n"
    html += voorwoord_block(latest, animate=True)
    html += "</div>\n" + footer("", scripts=("edities.js", "reveal.js", "edition.js"))
    open(os.path.join(OUT, "index.html"), "w").write(html)


def write_archive(articles, editions):
    html = head("Archief — De Dissident", "style.css", "Alle edities van De Dissident.")
    html += masthead("")
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
            html += (f'<li>'
                     f'<span class="toc-main"><a href="{a["url"]}">{esc(a["title"])}</a>{sub}</span>'
                     f'<span class="toc-author">{esc(a["author"])}</span></li>\n')
        html += "</ul>\n"

    html += "</main>\n" + footer("")
    open(os.path.join(OUT, "archief.html"), "w").write(html)


def edition_title(ed):
    return f"{ed['number']}e editie — De Dissident"


def expo_row_inner(ed, arts, editions):
    """De inhoud van .expo-row voor één editie: het vel plus de kolom ernaast.

    Los van write_edition() omdat edities.js precies dezelfde HTML meestuurt —
    zo wisselt edition.js in de browser naar exact wat de statische pagina zou
    tonen, zonder een tweede opmaak die uit de pas kan lopen."""
    theme = f" — {ed['theme']}" if ed.get("theme") else ""
    html = (f'<main id="inhoud" class="expo">\n'
            f'<h1 class="visually-hidden">{ed["number"]}e editie{esc(theme)}</h1>\n')
    html += exposition(ed, arts, editions, animate=True)
    html += "</main>\n"
    html += voorwoord_block(ed, animate=True)
    return html


def write_edition(ed, arts, editions):
    html = head(edition_title(ed), "style.css",
                f"Alle artikelen uit de {ed['number']}e editie van De Dissident.")
    html += masthead("")
    html += f'<div class="expo-row"{sheet_style(ed.get("accent"))}>\n'
    html += expo_row_inner(ed, arts, editions)
    html += "</div>\n" + footer("", scripts=("edities.js", "reveal.js", "edition.js"))
    open(os.path.join(OUT, f"editie-{ed['number']}.html"), "w").write(html)


def write_editions_js(all_articles, editions, latest):
    """Alle edities als kant-en-klare HTML, zodat edition.js kan wisselen
    zonder de pagina opnieuw te laden.

    Als los .js-bestand (en niet inline) om twee redenen: de browser cachet het
    één keer voor alle pagina's, en een <script>-tag werkt ook over file://,
    waar fetch() geblokkeerd is. Alleen markup — de foto's blijven losse
    bestanden die pas geladen worden als een editie echt getoond wordt."""
    bundel = {}
    for ed in editions:
        arts = [a for a in all_articles if a["edition_id"] == ed["id"]]
        bundel[str(ed["number"])] = {
            "url": f"editie-{ed['number']}.html",
            "title": edition_title(ed),
            "vars": sheet_vars(ed.get("accent")),
            "html": expo_row_inner(ed, arts, editions),
        }
    payload = json.dumps(bundel, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(OUT, "edities.js"), "w") as f:
        f.write("window.DD_EDITIES=" + payload + ";\n")
        f.write(f"window.DD_EDITIE_LAATSTE={latest['number']};\n")
        # De voorpagina toont de nieuwste editie maar heeft een eigen titel;
        # zonder dit zou de tab na een stap terug "7e editie" blijven zeggen.
        f.write("window.DD_TITEL_HOME=" + json.dumps(HOME_TITLE) + ";\n")


def write_404():
    html = head("Pagina niet gevonden — De Dissident", "style.css")
    html += masthead("")
    html += """<main id="inhoud">
<h1 class="page-title">Deze pagina bestaat niet</h1>
<p class="page-intro">Misschien is het artikel verplaatst of de link verouderd.</p>
<p class="back"><a href="index.html">← Naar de voorpagina</a> &nbsp;·&nbsp;
   <a href="archief.html">Blader door het archief</a></p>
</main>
"""
    html += footer("")
    open(os.path.join(OUT, "404.html"), "w").write(html)


def write_index_json(articles, editions):
    idx = [{
        "t": a["title"], "s": a["subtitle"], "c": a["category"], "a": a["author"],
        "e": a["edition_number"], "u": a["url"], "p": a["page"],
        "x": " ".join(a["paras"])[:1200],
    } for a in articles]
    # Editielabels apart van de artikelen: de zoek-overlay groepeert per editie
    # net als het archief, en heeft daarvoor de datum/het thema nodig zonder
    # dat op elk artikel te herhalen.
    eds = [{
        "n": ed["number"], "l": ed["date_label"], "t": ed.get("theme") or "",
        "u": f"editie-{ed['number']}.html",
    } for ed in editions]
    payload = json.dumps(idx, ensure_ascii=False, separators=(",", ":"))
    eds_payload = json.dumps(eds, ensure_ascii=False, separators=(",", ":"))
    json.dump(idx, open(os.path.join(OUT, "search-index.json"), "w"), ensure_ascii=False)
    # Also emit the index as a script: browsers block fetch() over file://, so
    # opening site/index.html straight from Finder would otherwise kill search.
    with open(os.path.join(OUT, "search-index.js"), "w") as f:
        f.write("window.DD_INDEX=" + payload + ";\n")
        f.write("window.DD_EDITIONS=" + eds_payload + ";\n")


if __name__ == "__main__":
    build()
