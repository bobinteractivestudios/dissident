#!/usr/bin/env python3
"""Stelt per artikel een accentkleur en pull quotes voor, uitgelezen uit de PDF.

    python3 tools/extract_accents.py ed7

Drukt JSON af die je in content/site.json kunt overnemen. Het is een hulpmiddel,
geen bouwstap: welke quote je wilt tonen blijft een redactionele keuze.
"""
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP = os.path.dirname(ROOT)

# Kleuren die overal voorkomen en dus nooit een accent zijn.
NEUTRAAL = re.compile(r"^#(0[0-9a-f]|1[0-9a-f]|2[0-3])", re.I)
GRIJS_TOL = 12


def is_neutraal(hexkleur):
    r = int(hexkleur[1:3], 16)
    g = int(hexkleur[3:5], 16)
    b = int(hexkleur[5:7], 16)
    if max(r, g, b) - min(r, g, b) <= GRIJS_TOL:      # grijs, zwart of wit
        return True
    return False


def spans(page):
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if s["text"].strip():
                    yield s


def accent(doc, first, last):
    """De meest gebruikte niet-neutrale kleur over het paginabereik."""
    weeg = collections.Counter()
    for n in range(first, last + 1):
        page = doc[n - 1]
        for s in spans(page):
            hexk = "#%06x" % s["color"]
            if is_neutraal(hexk):
                continue
            # grote letters wegen zwaarder: daar zit de huisstijl
            weeg[hexk] += len(s["text"].strip()) * (2 if s["size"] >= 20 else 1)
        for d in page.get_drawings():
            for key in ("fill", "color"):
                c = d.get(key)
                if not c:
                    continue
                hexk = "#%02x%02x%02x" % tuple(int(round(x * 255)) for x in c)
                if not is_neutraal(hexk):
                    weeg[hexk] += 40
    if not weeg:
        return None
    # bijna gelijke tinten samenvoegen (drukwerk levert #ee2f2d én #ee2a2b)
    samen = collections.Counter()
    for k, v in weeg.items():
        sleutel = next((s for s in samen if dicht_bij(s, k)), k)
        samen[sleutel] += v
    return samen.most_common(1)[0][0]


def dicht_bij(a, b, tol=24):
    return all(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) <= tol
               for i in (1, 3, 5))


def pullquotes(doc, first, last, body_size=14.0):
    """Blokken die groter gezet zijn dan de broodtekst."""
    uit = []
    for n in range(first, last + 1):
        for b in doc[n - 1].get_text("dict")["blocks"]:
            regels = []
            maat = 0
            for l in b.get("lines", []):
                for s in l["spans"]:
                    t = s["text"].strip()
                    if t:
                        regels.append(t)
                        maat = max(maat, s["size"])
            if not regels or maat <= body_size + 0.5:
                continue
            tekst = re.sub(r"\s+", " ", " ".join(regels)).strip()
            woorden = len(tekst.split())
            if 6 <= woorden <= 70:
                uit.append({"size": round(maat, 1), "page": n, "text": tekst})
    return uit


def main(edition_id):
    import fitz
    data = json.load(open(os.path.join(ROOT, "content", "site.json")))
    ed = next(e for e in data["editions"] if e["id"] == edition_id)
    pdf = os.path.join(DESKTOP, data["site"]["sources"][ed["pdf"]])
    doc = fitz.open(pdf)
    per_sheet = ed.get("pages_per_sheet", 1)

    for art in ed["articles"]:
        if not art.get("page"):
            continue
        first = (art["page"] + per_sheet - 1) // per_sheet
        last = (art["end"] + per_sheet - 1) // per_sheet if art.get("end") else first
        print("=" * 70)
        print(art["title"], f"(pdf {first}-{last})")
        print("  accent:", accent(doc, first, last))
        for q in pullquotes(doc, first, last):
            print(f"  [{q['size']:>5}] {q['text'][:150]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ed7")
