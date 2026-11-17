from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from app.research.citations import SourceRef
from app.research.explainer import EXPLAINER_SCHEMA_VERSION, Explainer, ExplainerSection, Understood

from .answer_sections import SectionOutcome
from .explainer_events import shown_title

__all__ = ["explainer_document"]


def explainer_document(
    *,
    answer_id: uuid.UUID,
    question: str,
    understood: Understood,
    outcomes: Sequence[SectionOutcome],
    titles: Mapping[str, str],
    follow_ups: Sequence[str],
) -> Explainer | None:
    if not any(outcome.blocks for outcome in outcomes):
        return None
    sections = [_section(outcome, titles) for outcome in sorted(outcomes, key=lambda o: o.spec.order)]
    known = {sid: ref for outcome in outcomes for sid, ref in outcome.sources.items()}
    cited = dict.fromkeys(
        sid for section in sections for block in section.blocks for sid in block.cited_source_ids()
    )
    return Explainer(
        schema_version=EXPLAINER_SCHEMA_VERSION,
        answer_id=answer_id,
        question=question,
        understood=understood,
        sections=sections,
        sources=[SourceRef.model_validate(known[source_id]) for source_id in cited],
        follow_ups=list(follow_ups),
        created_at=datetime.now(UTC),
    )


def _section(outcome: SectionOutcome, titles: Mapping[str, str]) -> ExplainerSection:
    spec = outcome.spec
    return ExplainerSection.model_validate(
        {
            "id": spec.id,
            "discipline": spec.discipline,
            **shown_title(spec, titles),
            "order": spec.order,
            "state": "READY" if outcome.blocks else "EMPTY",
            "blocks": [block.model_dump(mode="json", by_alias=True) for block in outcome.blocks],
            "searched": None if outcome.blocks else outcome.searched,
        }
    )
