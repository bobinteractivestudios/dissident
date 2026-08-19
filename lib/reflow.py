"""Turn pypdf layout-mode page text into ordered, column-aware paragraphs."""
import re
import unicodedata

LIG = {
    "ĳ": "ij", "Ĳ": "IJ",
    "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff",
    "ﬃ": "ffi", "ﬄ": "ffl",
    "’": "’", "­": "",
}

RUNNING_HEAD = re.compile(
    r"^\s*(\d{1,3}\s*)?De\s+Dissident\b.*?editie\b.*$", re.I)
FOLIO = re.compile(r"^\s*\d{1,3}\s*$")


def normalise(s):
    for k, v in LIG.items():
        s = s.replace(k, v)
    # ligature glyphs that extract as "fi" + padding spaces
    s = re.sub(r"\b(fi|fl|ffi|ffl)\s{2,}(?=[a-z])", r"\1", s)
    return s


def split_columns(lines, min_gutter=4, thresh_frac=0.10):
    """Split a block of layout-padded lines into columns at vertical whitespace runs."""
    if not lines:
        return []
    width = max(len(l) for l in lines)
    padded = [l.ljust(width) for l in lines]
    ink = [0] * width
    for l in padded:
        for i, ch in enumerate(l):
            if ch != " ":
                ink[i] += 1

    # A gutter is a run of near-empty character columns, not strictly empty ones:
    # a single long italic line can bleed a character or two into the gap.
    nlines = sum(1 for l in lines if l.strip())
    thresh = max(1, int(nlines * thresh_frac))

    # Find gutter runs, then cut at their midpoint so characters that bleed a
    # little way into the gap stay with the column they belong to.
    gutters = []
    run = None
    for i in range(width + 1):
        empty = i < width and ink[i] <= thresh
        if empty:
            if run is None:
                run = i
        else:
            if run is not None and i - run >= min_gutter:
                gutters.append((run, i))
            run = None

    cuts = [0] + [(a + b) // 2 for a, b in gutters] + [width]
    bounds = [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)]

    # Drop slivers (page furniture, rules, folios) and empty leading/trailing gaps.
    bounds = [(a, b) for a, b in bounds if b - a >= 12]
    if not bounds:
        return []

    # Assign whole runs of text to the column they start in, rather than slicing
    # each line at the boundary — a display line set wider than the body column
    # would otherwise lose the characters that cross it.
    cols = [[] for _ in bounds]
    for line in padded:
        buckets = [""] * len(bounds)
        for m in re.finditer(r"\S+(?: \S+)*", line):
            idx = 0
            for j, (a, b) in enumerate(bounds):
                if a <= m.start() < b:
                    idx = j
                    break
                if m.start() >= b:
                    idx = j
            text = m.group(0)
            buckets[idx] = (buckets[idx] + " " + text).strip() if buckets[idx] else text
        for j, b in enumerate(buckets):
            cols[j].append(b)
    return cols


def undouble(line):
    """Some editions carry a duplicate text layer, so every rendered line
    extracts twice in a row. Collapse "A B A B" back to "A B"."""
    words = line.split()
    n = len(words)
    if n >= 4 and n % 2 == 0:
        half = n // 2
        if words[:half] == words[half:]:
            return " ".join(words[:half])
    return line


def column_paragraphs(col_lines):
    """Group a column's lines into paragraphs, de-hyphenating line breaks."""
    paras = []
    buf = []
    for raw in col_lines:
        line = raw.strip()
        if not line or FOLIO.match(line) or RUNNING_HEAD.match(line):
            if buf:
                paras.append(buf)
                buf = []
            continue
        buf.append(line)
    if buf:
        paras.append(buf)

    out = []
    for p in paras:
        text = ""
        for line in p:
            line = re.sub(r"\s{2,}", " ", line)
            line = undouble(line)
            if text.endswith("-") and re.match(r"^[a-zà-ÿ]", line):
                text = text[:-1] + line
            elif text:
                text += " " + line
            else:
                text = line
        text = re.sub(r"\s+", " ", text).strip()
        text = undouble_prefix(text)
        if text:
            out.append(text)
    return out


def doubling_ratio(layout_text):
    """Fraction of lines that are a rendered line repeated twice in a row.

    Some editions were exported with a duplicate text layer; in layout mode the
    two copies land side by side and the hyphenated ones cannot be split apart
    again, so those pages are better read in plain mode instead."""
    lines = [l.strip() for l in normalise(layout_text).split("\n")]
    lines = [l for l in lines if len(l.split()) >= 4]
    if not lines:
        return 0.0
    doubled = sum(1 for l in lines if undouble(l) != l)
    return doubled / len(lines)


def page_paragraphs(layout_text, plain_text=None):
    """Full pipeline for one page of layout-mode text."""
    if plain_text and doubling_ratio(layout_text) > 0.25:
        return plain_paragraphs(plain_text)
    t = normalise(layout_text)
    lines = t.split("\n")
    paras = []
    for col in split_columns(lines):
        paras.extend(column_paragraphs(col))
    return paras


def plain_paragraphs(plain_text):
    """Fallback for duplicate-layer pages: plain extraction, one column order."""
    t = normalise(plain_text)
    return column_paragraphs(t.split("\n"))


def is_body(p, min_words=12):
    """Filter out captions, labels and stray fragments."""
    words = p.split()
    if len(words) < min_words:
        return False
    letters = sum(c.isalpha() for c in p)
    if letters < len(p) * 0.6:
        return False
    return True


def _fold(s):
    """Lowercase and strip diacritics, keeping the string the same length."""
    out = []
    for c in s.lower():
        d = unicodedata.normalize("NFKD", c)
        d = "".join(ch for ch in d if not unicodedata.combining(c))
        out.append(d[0] if d else c)
    return "".join(out)


def undouble_prefix(p, min_run=12):
    """Drop a duplicated opening run left by a duplicate text layer.

    On pages that are not doubled enough overall to trigger the plain-mode
    fallback, the display type still lands twice in one paragraph — as in
    "Een Interview Met Frederik JansenEen Interview Met Frederik Jansen Het
    gelijkheidsdenken…". The give-away is that the second copy starts exactly
    where the first ends; prose that merely repeats a phrase has text in
    between, so requiring adjacency leaves real sentences alone.

    One copy is kept, because the doubled run is sometimes real prose rather
    than a heading and throwing both away would lose it."""
    flat = _fold(p)
    for k in range(min_run, len(flat) // 2 + 1):
        if flat[:k] == flat[k:2 * k]:
            return p[k:].lstrip()
        # the two copies are sometimes separated by a single space
        if flat[k:k + 1] == " " and flat[:k] == flat[k + 1:2 * k + 1]:
            return p[k + 1:].lstrip()
    return p
