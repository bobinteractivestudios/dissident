#!/usr/bin/env python3
"""Stelt per artikel pull quotes voor, uitgelezen uit de PDF.

    python3 tools/extract_pullquotes.py ed7

Drukt ze af — dit schrijft niets weg. Welke quote je uiteindelijk toont in
"pullquotes" in content/site.json blijft een redactionele keuze.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP = os.path.dirname(ROOT)


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
        for q in pullquotes(doc, first, last):
            print(f"  [{q['size']:>5}] {q['text'][:150]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ed7")
