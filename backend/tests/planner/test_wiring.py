from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.planner.reading import LiveSources
from app.providers import router
from app.providers.structured import router_structured_model
from app.research.structured import StructuredModel
from app.services import live_sources as live_sources_module
from app.services.ai_providers import AiTask
from app.sources.scholarly.registry import ScholarlyKeys
from app.sources.web.registry import WebSearchConfig


async def test_the_router_model_runs_the_plan_task_with_the_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    async def run(task: AiTask, **options: Any) -> SimpleNamespace:
        seen.update(options, task=task)
        return SimpleNamespace(text='{"ok": true}', degraded=True)

    monkeypatch.setattr(router, "run", run)
    principal = router.Principal(role="STUDENT")
    model = router_structured_model(AiTask.PLAN, principal)
    assert isinstance(model, StructuredModel)
    reply = await model(system="sys", user="usr", schema={"type": "object"})
    assert (reply.text, reply.degraded) == ('{"ok": true}', True)
    assert seen == {
        "task": AiTask.PLAN,
        "system": "sys",
        "user": "usr",
        "json_schema": {"type": "object"},
        "principal": principal,
    }


async def test_live_sources_join_every_adapter_with_one_fetcher(monkeypatch: pytest.MonkeyPatch) -> None:
    async def keys(session: object) -> ScholarlyKeys:
        return ScholarlyKeys(contact_email="research@example.org")

    async def web_config(session: object) -> WebSearchConfig:
        return WebSearchConfig(searxng_url="http://127.0.0.1:8888")

    monkeypatch.setattr(live_sources_module, "scholarly_keys", keys)
    monkeypatch.setattr(live_sources_module, "web_search_config", web_config)
    async with httpx.AsyncClient() as client:
        sources = await live_sources_module.live_sources(object(), client)
    assert isinstance(sources, LiveSources)
    names = [searcher.name for searcher in sources.searchers]
    assert names == [
        "openalex",
        "crossref",
        "semantic_scholar",
        "europe_pmc",
        "arxiv",
        "doaj",
        "wikipedia",
        "wikidata",
        "pubchem",
        "wikimedia_commons",
        "web",
    ]
    assert {searcher.tier for searcher in sources.searchers[:-1]} == {"T3"}
    assert sources.searchers[-1].tier == "T4"
    assert sources.doi_source is not None and sources.doi_source.name == "crossref"
    assert sources.locator is not None and sources.locator.name == "unpaywall"
    assert sources.searchers[-1].primary.fetcher is sources.fetcher
