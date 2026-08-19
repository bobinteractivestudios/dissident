"""Minimal reader for Apple iWork .iwa files: IWA chunk framing + raw Snappy blocks."""
import sys, struct, re, zipfile, io


def snappy_decompress(data):
    """Pure-python raw Snappy block decompressor."""
    pos = 0
    # varint uncompressed length
    length = 0
    shift = 0
    while True:
        b = data[pos]
        pos += 1
        length |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7

    out = bytearray()
    n = len(data)
    while pos < n:
        tag = data[pos]
        pos += 1
        t = tag & 0x03
        if t == 0:  # literal
            ln = tag >> 2
            if ln < 60:
                ln += 1
            else:
                extra = ln - 59
                ln = int.from_bytes(data[pos:pos + extra], "little") + 1
                pos += extra
            out += data[pos:pos + ln]
            pos += ln
        else:
            if t == 1:
                ln = 4 + ((tag >> 2) & 0x07)
                off = ((tag >> 5) << 8) | data[pos]
                pos += 1
            elif t == 2:
                ln = (tag >> 2) + 1
                off = int.from_bytes(data[pos:pos + 2], "little")
                pos += 2
            else:
                ln = (tag >> 2) + 1
                off = int.from_bytes(data[pos:pos + 4], "little")
                pos += 4
            if off == 0 or off > len(out):
                break
            start = len(out) - off
            for i in range(ln):
                out.append(out[start + i])
    return bytes(out)


def iwa_chunks(raw):
    """Yield decompressed payloads from IWA chunk framing."""
    pos = 0
    n = len(raw)
    while pos + 4 <= n:
        header = raw[pos:pos + 4]
        pos += 4
        ln = int.from_bytes(header[1:4], "little")
        block = raw[pos:pos + ln]
        pos += ln
        if not block:
            continue
        try:
            yield snappy_decompress(block)
        except Exception:
            continue


def readable_strings(buf, minlen=3):
    """Pull UTF-8 text runs out of a protobuf payload."""
    out = []
    cur = bytearray()

    def flush():
        if len(cur) >= minlen:
            s = cur.decode("utf-8", errors="replace").replace("�", "")
            if len(s) >= minlen:
                out.append(s)

    for b in buf:
        if 32 <= b < 127 or b in (9, 10, 13) or b >= 0x80:
            cur.append(b)
        else:
            flush()
            cur = bytearray()
    flush()
    return out


def extract(pages_path):
    z = zipfile.ZipFile(pages_path)
    names = [n for n in z.namelist() if n.endswith(".iwa") and "Document" in n]
    texts = []
    for name in names:
        raw = z.read(name)
        for payload in iwa_chunks(raw):
            texts.extend(readable_strings(payload))
    return texts


if __name__ == "__main__":
    for s in extract(sys.argv[1]):
        # keep runs that look like prose
        if len(s) > 30 and re.search(r"[a-z]{4}\s+[a-z]{3}", s):
            print(s)
            print("---")
