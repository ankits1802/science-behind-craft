from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from app.curation.parts import Source

from curation.polite import Fetched, FetchFailed
from curation.reading import ReadFailed, SourceText, source_text

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "backend" / "tests" / "curation" / "fixtures"
PASSING = FIXTURES / "passing" / "Kutch-Ajrakh.json"
FAILING = FIXTURES / "failing" / "Kutch-Ajrakh.json"
SOURCES = FIXTURES / "sources"
RECORDED = {
    "https://example.org/test/block-printing": SOURCES / "block-printing.txt",
    "https://example.org/test/printing-village": SOURCES / "printing-village.txt",
}
NOW = datetime(2026, 11, 17, 7, 0, tzinfo=UTC)


def fetched(
    url: str, body: bytes, media_type: str = "text/plain", *, final_url: str | None = None
) -> Fetched:
    return Fetched(
        url=url,
        final_url=final_url or url,
        status=200,
        media_type=media_type,
        charset="utf-8",
        body=body,
        fetched_at=NOW,
    )


def recorded_reader(*, unread: frozenset[str] = frozenset()) -> Callable[[Source], SourceText]:
    def read(source: Source) -> SourceText:
        if source.id in unread:
            raise ReadFailed(
                source.url, ["live page: HTTP 403", "archive: the Wayback Machine has no snapshot"]
            )
        content_type, text, truncated = source_text(fetched(source.url, RECORDED[source.url].read_bytes()))
        return SourceText(
            url=source.url,
            route="LIVE",
            read_url=source.url,
            final_url=source.url,
            fetched_at=NOW,
            content_type=content_type,
            text=text,
            truncated=truncated,
        )

    return read


class FakeHttp:
    def __init__(self, answers: Mapping[str, Fetched | FetchFailed]) -> None:
        self.answers = answers
        self.asked: list[str] = []

    def get(self, url: str) -> Fetched:
        self.asked.append(url)
        answer = self.answers[url]
        if isinstance(answer, FetchFailed):
            raise answer
        return answer


def pdf_with_text(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)
