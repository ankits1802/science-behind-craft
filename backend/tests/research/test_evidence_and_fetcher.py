import hashlib

import pytest
from pydantic import ValidationError

from app.research.evidence import (
    EvidenceItem,
    OpenAccessLocation,
    SearchQuery,
    SourceAdapter,
    SourceDocument,
)
from app.research.fetcher import FETCH_MAX_BYTES, FetchedPage, Fetcher, FetchRequest

from .fixtures import RETRIEVED, evidence_item

PAGE = "Results. In practice, alum forms a red lake with alizarin at about 60 °C on the fibre."
PAGE_SHA256 = hashlib.sha256(PAGE.encode("utf-8")).hexdigest()


def test_an_evidence_item_names_its_adapter_and_is_https() -> None:
    item = evidence_item()
    assert item.id == "openalex:W2019"
    assert item.model_dump(mode="json")["retrievedAt"] == "2026-11-16T09:30:00Z"
    for changes in [
        {"id": "crossref:W2019"},
        {"id": "openalex:"},
        {"url": "http://example.org/paper"},
        {"retrievedAt": "2026-11-16T09:30:00"},
        {"published": "2019-13"},
        {"trust": "E"},
        {"tier": "T2"},
        {"adapter": "Open Alex"},
        {"doi": "doi:10.1000/x"},
    ]:
        with pytest.raises(ValidationError):
            evidence_item(**changes)


def test_sources_dedupe_by_doi_then_canonical_url() -> None:
    assert evidence_item().source_key == "doi:10.1000/example.2019.1"
    item = evidence_item(doi=None, url="https://Example.ORG:443/a/b/?q=1#section-2")
    assert item.source_key == "url:https://example.org/a/b?q=1"
    assert evidence_item(doi=None, url="https://example.org").source_key == "url:https://example.org/"


def test_a_source_document_backs_every_quote() -> None:
    document = SourceDocument(
        item=evidence_item(), text=PAGE, text_sha256=PAGE_SHA256, truncated=False, content="ABSTRACT"
    )
    assert document.item.quotes[0].locator == "p. 12"
    with pytest.raises(ValidationError):
        SourceDocument(
            item=evidence_item(), text=PAGE, text_sha256="0" * 64, truncated=False, content="ABSTRACT"
        )
    other = "Results. Alum and iron were both used."
    with pytest.raises(ValidationError):
        SourceDocument(
            item=evidence_item(),
            text=other,
            text_sha256=hashlib.sha256(other.encode("utf-8")).hexdigest(),
            truncated=False,
            content="FULL_TEXT",
        )


class FakeAdapter:
    name = "openalex"
    tier = "T3"

    async def search(self, query: SearchQuery, k: int) -> list[EvidenceItem]:
        return [evidence_item()][:k]

    async def fetch(self, item_id: str) -> SourceDocument:
        return SourceDocument(
            item=evidence_item(id=item_id),
            text=PAGE,
            text_sha256=PAGE_SHA256,
            truncated=False,
            content="FULL_TEXT",
        )


async def test_an_adapter_meets_the_protocol_end_to_end() -> None:
    adapter = FakeAdapter()
    assert isinstance(adapter, SourceAdapter)
    hits = await adapter.search(SearchQuery(text="Ajrakh alum"), 5)
    document = await adapter.fetch(hits[0].id)
    assert document.item.source_key == hits[0].source_key


def test_fetch_requests_may_tighten_caps_but_never_loosen_them() -> None:
    request = FetchRequest(url="https://example.org/a.pdf")
    assert (request.timeout_seconds, request.max_bytes) == (10.0, 3 * 1024 * 1024)
    assert FetchRequest(url="https://example.org/", max_bytes=1024).max_bytes == 1024
    for changes in [
        {"timeoutSeconds": 30},
        {"maxBytes": FETCH_MAX_BYTES + 1},
        {"url": "http://example.org/"},
        {"url": "https://exa mple.org/"},
    ]:
        with pytest.raises(ValidationError):
            FetchRequest.model_validate({"url": "https://example.org/", **changes})


def page(**changes: object) -> FetchedPage:
    fields: dict[str, object] = {
        "url": "https://example.org/a",
        "finalUrl": "https://example.org/b",
        "redirects": ["https://example.org/b"],
        "status": 200,
        "contentType": "text/html",
        "bytes": 2048,
        "sha256": "a" * 64,
        "fetchedAt": RETRIEVED,
        "text": PAGE,
        "truncated": False,
        "metadata": {"title": "Alizarin lakes", "published": "2019"},
    }
    fields.update(changes)
    return FetchedPage.model_validate(fields)


def test_a_fetched_page_records_its_redirect_chain() -> None:
    assert page().final_url == "https://example.org/b"
    assert page(redirects=[], finalUrl="https://example.org/a").redirects == []
    for changes in [
        {"finalUrl": "https://example.org/c"},
        {"redirects": ["https://example.org/r"] * 4, "finalUrl": "https://example.org/r"},
        {"status": 404},
        {"contentType": "image/png"},
        {"bytes": FETCH_MAX_BYTES + 1},
    ]:
        with pytest.raises(ValidationError):
            page(**changes)


def test_the_fetcher_protocol_is_one_call() -> None:
    class Sandbox:
        async def fetch(self, request: FetchRequest) -> FetchedPage:
            return page(url=request.url)

    assert isinstance(Sandbox(), Fetcher)


def test_an_open_access_location_names_a_doi_and_a_known_status() -> None:
    found = OpenAccessLocation(
        doi="10.1038/s41598-022-27110-0",
        status="GOLD",
        pdf_url="https://www.nature.com/articles/s41598-022-27110-0.pdf",
        host_type="PUBLISHER",
        checked_at=RETRIEVED,
    )
    assert found.is_open
    assert found.model_dump(mode="json", exclude_none=True) == {
        "doi": "10.1038/s41598-022-27110-0",
        "status": "GOLD",
        "pdfUrl": "https://www.nature.com/articles/s41598-022-27110-0.pdf",
        "hostType": "PUBLISHER",
        "checkedAt": "2026-11-16T09:30:00Z",
    }
    closed = OpenAccessLocation(doi="10.1111/cote.12288", status="CLOSED", checked_at=RETRIEVED)
    assert not closed.is_open
    for changes in [
        {"status": "PLATINUM"},
        {"doi": "cote.12288"},
        {"status": "CLOSED", "landingUrl": "https://doi.org/10.1111/cote.12288"},
        {"pdfUrl": "http://example.org/a.pdf"},
        {"checkedAt": "2026-11-16T09:30:00"},
    ]:
        with pytest.raises(ValidationError):
            OpenAccessLocation.model_validate(
                {"doi": "10.1111/cote.12288", "status": "GREEN", "checkedAt": RETRIEVED} | changes
            )
