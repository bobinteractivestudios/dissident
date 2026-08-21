#!/usr/bin/env python3
"""Leest de artikelteksten uit de magazine-PDF's en schrijft ze naar content/tekst/.

    python3 tools/extract_text.py            # alle edities, slaat bestaande over
    python3 tools/extract_text.py ed7        # alleen editie 7
    python3 tools/extract_text.py ed7 --force  # ook al bestaande opnieuw uitlezen

Dit hoort niet bij het bouwen van de site. Draai het één keer als er een nieuwe
editie bij komt; daarna leest build.py alleen nog de bestanden in content/tekst/.

Vereist pypdf:  pip install pypdf
"""
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP = os.path.dirname(ROOT)
CONTENT = os.path.join(ROOT, "content")
TEKST = os.path.join(CONTENT, "tekst")

sys.path.insert(0, os.path.join(ROOT, "lib"))


def from_pdf(rel_path, start, end):
    """Alinea's uit een paginabereik van één PDF."""
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("pypdf ontbreekt. Installeer het met:\n\n    pip3 install pypdf\n")
    import reflow

    path = os.path.join(DESKTOP, rel_path)
    if not os.path.exists(path):
        print(f"    ! PDF niet gevonden: {rel_path}")
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


def strip_running_head(paras, title, look_at=3, max_words=40):
    """Haalt openingsalinea's weg die eigenlijk de kopregel van het blad zijn.

    Die kopregel herhaalt de artikeltitel boven aan elke pagina en belandt in de
    tekst als een kort, titelvormig fragment — vaak met de letterspatiëring van
    de displayletter verhaspeld ("In Gesprek Met Ug is Nastevicis Nastevic")."""
    def fold(s):
        s = unicodedata.normalize("NFKD", s.lower())
        s = "".join(c for c in s if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]", "", s)

    key = fold(title)[:13]
    if len(key) < 8:
        return paras

    out = list(paras)
    while out and len(out[0].split()) <= max_words and fold(out[0]).startswith(key):
        out.pop(0)
        if len(paras) - len(out) >= look_at:
            break
    return out


def article_range(edition, art):
    """Paginabereik in de PDF; rekent spreads om naar bladpagina's."""
    per_sheet = edition.get("pages_per_sheet", 1)
    start = (art["page"] + per_sheet - 1) // per_sheet
    end = art.get("end")
    end = (end + per_sheet - 1) // per_sheet if end else None
    return start, end


def fill_ends(articles):
    """Een artikel loopt tot de pagina vóór het volgende, tenzij 'end' vaststaat."""
    for i, art in enumerate(articles):
        if art.get("end") is None and art.get("page"):
            nxt = next((a["page"] for a in articles[i + 1:] if a.get("page")), None)
            art["end"] = nxt - 1 if nxt else None


def main(argv):
    only = next((a for a in argv if not a.startswith("-")), None)
    force = "--force" in argv

    data = json.load(open(os.path.join(CONTENT, "site.json")))
    sources = data["site"]["sources"]
    os.makedirs(TEKST, exist_ok=True)

    geschreven = overgeslagen = leeg = 0
    for ed in data["editions"]:
        if only and ed["id"] != only:
            continue
        if not ed.get("pdf"):
            continue

        print(f"{ed['id']} — {ed['date_label']}")
        fill_ends(ed["articles"])

        for art in ed["articles"]:
            if not art.get("page"):
                continue
            dest = os.path.join(TEKST, f"{ed['id']}-p{art['page']}.json")
            if os.path.exists(dest) and not force:
                overgeslagen += 1
                continue

            start, end = article_range(ed, art)
            paras = strip_running_head(
                from_pdf(sources[ed["pdf"]], start, end), art["title"])
            json.dump({"paras": paras}, open(dest, "w"),
                      ensure_ascii=False, indent=1)

            woorden = sum(len(p.split()) for p in paras)
            print(f"  {art['title'][:46]:<48} {woorden:>5} woorden")
            geschreven += 1
            if not paras:
                leeg += 1

    print(f"\n{geschreven} geschreven, {overgeslagen} overgeslagen"
          f"{f', {leeg} zonder tekst' if leeg else ''}")
    if overgeslagen and not force:
        print("Gebruik --force om bestaande opnieuw uit te lezen.")


if __name__ == "__main__":
    main(sys.argv[1:])
