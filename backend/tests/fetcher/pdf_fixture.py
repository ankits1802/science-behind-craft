from __future__ import annotations


def _escaped(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_with_pages(
    texts: list[str], *, title: str | None = None, author: str | None = None, created: str | None = None
) -> bytes:
    page_ids = [4 + 2 * index for index in range(len(texts))]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            "<< /Type /Pages /Kids ["
            + " ".join(f"{pid} 0 R" for pid in page_ids)
            + f"] /Count {len(texts)} >>"
        ).encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for page_id, text in zip(page_ids, texts, strict=True):
        stream = f"BT /F1 12 Tf 72 720 Td ({_escaped(text)}) Tj ET".encode("latin-1")
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>"
        ).encode()
        objects[page_id + 1] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
    info_id = None
    info = {"Title": title, "Author": author, "CreationDate": created}
    if any(info.values()):
        info_id = max(objects) + 1
        entries = " ".join(f"/{key} ({_escaped(value)})" for key, value in info.items() if value)
        objects[info_id] = f"<< {entries} >>".encode("latin-1")
    return _assembled(objects, info_id)


def _assembled(objects: dict[int, bytes], info_id: int | None) -> bytes:
    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += b"%d 0 obj\n" % number + objects[number] + b"\nendobj\n"
    xref_at = len(out)
    size = max(objects) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for number in range(1, size):
        out += b"%010d 00000 n \n" % offsets[number]
    trailer = f"<< /Size {size} /Root 1 0 R" + (f" /Info {info_id} 0 R" if info_id else "") + " >>"
    out += b"trailer\n" + trailer.encode() + b"\nstartxref\n%d\n%%%%EOF\n" % xref_at
    return bytes(out)
