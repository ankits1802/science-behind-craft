from __future__ import annotations

import io
from typing import Any

from pypdf import PdfReader
from pypdf.errors import LimitReachedError

from app.research.fetcher import PDF_MAX_DECOMPRESSED_BYTES, PDF_MAX_PAGES, FetchRefused, PageMetadata
from app.sources.records import clean_text, partial_date_of

__all__ = ["pdf_text"]


def pdf_text(
    url: str,
    body: bytes,
    *,
    max_pages: int = PDF_MAX_PAGES,
    max_decompressed: int = PDF_MAX_DECOMPRESSED_BYTES,
) -> tuple[str, bool, PageMetadata]:
    try:
        reader = _opened(url, body)
        page_count = len(reader.pages)
        texts = _page_texts(url, reader, min(page_count, max_pages), max_decompressed)
        metadata = _metadata(reader)
    except FetchRefused:
        raise
    except LimitReachedError:
        raise FetchRefused(url, "PDF_LIMIT", "a stream decompresses past the parser's limit") from None
    except Exception as error:
        raise FetchRefused(url, "PARSE_FAILED", f"PDF could not be read ({type(error).__name__})") from None
    text = "\n\n".join(t for t in texts if t.strip())
    if not text.strip():
        raise FetchRefused(url, "PARSE_FAILED", "the PDF has no text layer")
    return text, page_count > max_pages, metadata


def _opened(url: str, body: bytes) -> PdfReader:
    reader = PdfReader(io.BytesIO(body), strict=False)
    if reader.is_encrypted and not reader.decrypt(""):
        raise FetchRefused(url, "PARSE_FAILED", "the PDF is encrypted")
    return reader


def _page_texts(url: str, reader: PdfReader, pages: int, max_decompressed: int) -> list[str]:
    texts: list[str] = []
    decompressed = 0
    for index in range(pages):
        page = reader.pages[index]
        contents = page.get_contents()
        decompressed += len(contents.get_data()) if contents is not None else 0
        if decompressed > max_decompressed:
            raise FetchRefused(url, "PDF_LIMIT", f"content past {max_decompressed} bytes by page {index + 1}")
        texts.append(page.extract_text() or "")
    return texts


def _metadata(reader: PdfReader) -> PageMetadata:
    info: Any = reader.metadata or {}
    title = clean_text(getattr(info, "title", None))
    author = clean_text(getattr(info, "author", None))
    created = getattr(info, "creation_date_raw", None)
    return PageMetadata(
        title=title[:1000] if title else None,
        authors=[author[:300]] if author else [],
        published=_pdf_date(created),
    )


def _pdf_date(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    digits = raw.removeprefix("D:")[:8]
    if len(digits) == 8 and digits.isdigit():
        return partial_date_of(f"{digits[:4]}-{digits[4:6]}-{digits[6:]}")
    if len(digits) >= 4 and digits[:4].isdigit():
        return partial_date_of(digits[:4])
    return None
