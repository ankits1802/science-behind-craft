import copy
from typing import Any

from app.research.explainer import Explainer
from app.research.explainer_versions import ExplainerVersionDocument
from app.services.explainer_payload import first_version_mark, version_document

from ..contracts.explainer_golden import DOCUMENT, citations_in, golden_json
from ..contracts.learning_golden import VERSIONS, learning

__all__ = ["base_version", "first_explainer", "follow_up_document", "latest_golden"]


def first_explainer() -> Explainer:
    return Explainer.model_validate(golden_json(DOCUMENT))


def base_version() -> ExplainerVersionDocument:
    explainer = first_explainer()
    mark = first_version_mark(
        answer_id=explainer.answer_id, question=explainer.question, created_at=explainer.created_at
    )
    return version_document(mark, explainer)


def latest_golden() -> dict[str, Any]:
    return copy.deepcopy(learning(VERSIONS)["latest"])


def follow_up_document(sections: list[dict[str, Any]], answer_id: str | None = None) -> Explainer:
    latest = latest_golden()["explainer"]
    cited = list(dict.fromkeys(citation["sourceId"] for citation in citations_in(sections)))
    known = {source["id"]: source for source in latest["sources"]}
    payload = {
        **latest,
        "answerId": answer_id or latest["answerId"],
        "understood": {**latest["understood"], "candidates": []},
        "sections": [{**section, "order": order} for order, section in enumerate(sections, start=1)],
        "sources": [known[source_id] for source_id in cited],
    }
    return Explainer.model_validate(payload)
