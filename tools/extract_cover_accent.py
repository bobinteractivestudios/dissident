#!/usr/bin/env python3
"""Leidt de accentkleur van een editie af uit haar covertekening en schrijft
"accent" in content/site.json bij die editie.

    python3 tools/extract_cover_accent.py            # alle edities met "cover"
    python3 tools/extract_cover_accent.py ed6 ed7     # specifieke edities

De coverkleur op papier is voor een drukpers gekozen en is op een zwart scherm
meestal te donker om als UI-accent te dienen (in de praktijk landt dat rond
V ≈ 0,25–0,30 in HSV, tegenover 0,45–0,95 bij een leesbaar accent). Deze tool
neemt daarom de tint (H) en verzadiging (S) van de dominante covertint zoals
gedrukt, en zet alleen de helderheid (V) naar een vaste, schermvriendelijke
waarde. De herkomst blijft zichtbaar in de kleur; alleen de belichting is
anders — net als een foto die van drukwerk naar scherm verhuist.

Vereist pypdf noch fitz voor gewone beelden; een cover die als PDF staat
aangeleverd (".pdf") wordt via PyMuPDF (fitz) gerasterd.
"""
import colorsys
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP = os.path.dirname(ROOT)

TARGET_V = 0.60       # helderheid van het uiteindelijke accent
MIN_SATURATION = 0.15  # onder dit niveau is de dominante tint te grijs om op te varen


def _laad_pdf_pagina(pad):
    import fitz
    doc = fitz.open(pad)
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(1.4, 1.4))
    from PIL import Image
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def dominante_tint(pad, thumb=48):
    """(h, s) van de meest voorkomende niet-neutrale kleur op de cover.

    Werkt op een kleine thumbnail: dat middelt fotodetail weg en laat het
    grote, egale achtergrondvlak van een covertekening domineren."""
    from PIL import Image

    im = (_laad_pdf_pagina(pad) if pad.lower().endswith(".pdf")
          else Image.open(pad).convert("RGB"))
    im = im.resize((thumb, thumb), Image.LANCZOS)

    tel = collections.Counter()
    for r, g, b in im.getdata():
        if max(r, g, b) - min(r, g, b) <= 14:  # grijs, zwart of wit: negeren
            continue
        tel[(r // 8 * 8, g // 8 * 8, b // 8 * 8)] += 1
    if not tel:
        return None

    (r, g, b), _ = tel.most_common(1)[0]
    h, s, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return h, s


def accent_hex(pad):
    tint = dominante_tint(pad)
    if tint is None:
        return None
    h, s = tint
    if s < MIN_SATURATION:
        return None
    r, g, b = colorsys.hsv_to_rgb(h, s, TARGET_V)
    return "#%02x%02x%02x" % tuple(round(c * 255) for c in (r, g, b))


def main(argv):
    p = os.path.join(ROOT, "content", "site.json")
    data = json.load(open(p))

    ids = [a for a in argv if not a.startswith("-")]
    edities = [e for e in data["editions"]
               if e.get("cover") and (not ids or e["id"] in ids)]
    if not edities:
        print("Geen edities met een 'cover' om uit te lezen.")
        return

    for ed in edities:
        pad = os.path.join(DESKTOP, ed["cover"])
        if not os.path.exists(pad):
            print(f"  ! {ed['id']}: cover niet gevonden op {ed['cover']}")
            continue
        hexk = accent_hex(pad)
        if not hexk:
            print(f"  ! {ed['id']}: cover te grijs/neutraal, geen accent bepaald")
            continue
        ed["accent"] = hexk
        print(f"  {ed['id']}  {hexk}   ({ed['cover']})")

    json.dump(data, open(p, "w"), ensure_ascii=False, indent=1)
    print(f"\ncontent/site.json bijgewerkt. Draai daarna python3 build.py.")


if __name__ == "__main__":
    main(sys.argv[1:])
