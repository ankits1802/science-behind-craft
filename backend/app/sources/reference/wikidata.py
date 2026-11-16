from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.errors import InvalidInput
from app.research.evidence import EvidenceItem, SearchQuery, SourceDocument

from ..adapter import Clock, HttpSourceAdapter, build_document, utc_now
from ..http import RatePolicy, SourceHttp
from ..records import UnusableRecord, clean_text, partial_date_of
from .mediawiki import (
    WIKIMEDIA_PUBLISHER,
    WIKIMEDIA_RATE,
    action_api,
    language_and_native,
    primary_language,
    with_language,
)
from .wikidata_statements import (
    ITEM_ID,
    Statement,
    external_ids_of,
    statement_lines,
    statements_from_bindings,
    statements_query,
)

__all__ = ["WIKIDATA_LICENCE", "WIKIDATA_RATE", "WIKIDATA_SPARQL_RATE", "WikidataAdapter"]

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WIKIDATA_RATE = WIKIMEDIA_RATE
WIKIDATA_SPARQL_RATE = RatePolicy(min_interval=1.0)
WIKIDATA_LICENCE = "CC0 1.0"
ENTITY_PROPS = "info|labels|descriptions|aliases"


class WikidataAdapter(HttpSourceAdapter):
    name = "wikidata"

    def __init__(self, http: SourceHttp, *, sparql: SourceHttp, clock: Clock = utc_now) -> None:
        super().__init__(http, clock=clock)
        self.sparql = sparql

    async def _search_records(self, query: SearchQuery, k: int) -> list[Any]:
        language = primary_language(query.language)
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query.text,
            "srnamespace": "0",
            "srlimit": str(k),
            "srprop": "",
        }
        payload = await action_api(self.http, WIKIDATA_API, params)
        hits = ((payload.get("query") or {}).get("search")) or []
        ids = [hit.get("title") for hit in hits if ITEM_ID.match(str(hit.get("title") or ""))]
        if not ids:
            return []
        entities = await self._entities(ids, language)
        return [(entities[item_id], language) for item_id in ids if item_id in entities]

    def _item(self, record: Any, retrieved_at: datetime) -> EvidenceItem:
        entity, language = record
        item_id = clean_text(entity.get("id"))
        if not item_id or not ITEM_ID.match(item_id) or "missing" in entity:
            raise UnusableRecord("no Wikidata item id")
        label = _term(entity, "labels", language)
        if label is None:
            raise UnusableRecord("no label")
        revision = str(entity.get("lastrevid") or "")
        if not revision:
            raise UnusableRecord("no revision")
        return EvidenceItem(
            id=f"{self.name}:{with_language(item_id, language)}",
            adapter=self.name,
            tier=self.tier,
            source_type="DATASET",
            url=f"https://www.wikidata.org/wiki/{item_id}",
            title=label,
            published=partial_date_of(entity.get("modified")),
            retrieved_at=retrieved_at,
            licence=WIKIDATA_LICENCE,
            attribution=f"Wikidata, {item_id}, revision {revision}",
            publisher=WIKIMEDIA_PUBLISHER,
            trust="B",
            external_ids={"wikidata": item_id, "revision": revision},
        )

    async def _fetch_document(self, native: str, retrieved_at: datetime) -> SourceDocument:
        language, item_id = language_and_native(native)
        if not ITEM_ID.match(item_id):
            raise InvalidInput(f"{native!r} is not a Wikidata item id")
        entities = await self._entities([item_id], language)
        if item_id not in entities:
            raise self._not_found(native, "no item")
        statements = await self._statements(item_id, language)
        entity = entities[item_id]
        item = self._item((entity, language), retrieved_at)
        item = item.model_copy(update={"external_ids": item.external_ids | external_ids_of(statements)})
        return build_document(item, _item_text(entity, language, statement_lines(statements)), "EXCERPT")

    async def _entities(self, ids: list[str], language: str) -> dict[str, dict[str, Any]]:
        params = {
            "action": "wbgetentities",
            "ids": "|".join(ids),
            "props": ENTITY_PROPS,
            "languages": language,
            "languagefallback": "1",
        }
        payload = await action_api(self.http, WIKIDATA_API, params)
        entities = payload.get("entities") or {}
        return {key: value for key, value in entities.items() if "missing" not in value}

    async def _statements(self, item_id: str, language: str) -> list[Statement]:
        response = await self.sparql.get(
            WIKIDATA_SPARQL,
            params={"query": statements_query(item_id, language), "format": "json"},
            headers={"Accept": "application/sparql-results+json"},
        )
        bindings = ((response.json(self.sparql.service).get("results")) or {}).get("bindings") or []
        return statements_from_bindings(bindings)


def _term(entity: dict[str, Any], terms: str, language: str) -> str | None:
    return clean_text(((entity.get(terms) or {}).get(language) or {}).get("value"))


def _item_text(entity: dict[str, Any], language: str, lines: list[str]) -> str:
    aliases = [clean_text(alias.get("value")) for alias in (entity.get("aliases") or {}).get(language) or []]
    parts = [f"{_term(entity, 'labels', language)} ({entity['id']})", _term(entity, "descriptions", language)]
    named = [alias for alias in aliases if alias]
    if named:
        parts.append(f"Also known as: {'; '.join(named)}")
    return "\n".join(part for part in [*parts, *lines] if part)
