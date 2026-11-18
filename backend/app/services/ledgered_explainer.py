from __future__ import annotations

import logging
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from pydantic import ValidationError

from app.research.blocks import BlockBase
from app.research.blocks_lede import LedeBlock
from app.research.explainer import Block, Explainer, ExplainerSection

from .claim_ledger import COVERED_NOTE, ClaimLedger, admission_batches

__all__ = ["ledgered_explainer"]

logger = logging.getLogger(__name__)

SourceRefs = Mapping[str, Mapping[str, Any]]


def ledgered_explainer(explainer: Explainer, known: SourceRefs = MappingProxyType({})) -> Explainer:
    try:
        return _rebuilt(explainer, known)
    except ValidationError as refused:
        logger.error("the ledger left answer %s off its contract: %s", explainer.answer_id, refused)
        return explainer


def _rebuilt(explainer: Explainer, known: SourceRefs) -> Explainer:
    ledger = ClaimLedger()
    refs = {
        **known,
        **{source.id: source.model_dump(mode="json", by_alias=True) for source in explainer.sources},
    }
    lede = _lede(ledger, explainer, refs)
    sections = [_section(ledger, section, refs) for section in explainer.sections]
    for source_id, ref in refs.items():
        ledger.sources.register(source_id, ref)
    merged = ledger.sources.refs()
    shown: list[BlockBase] = [*([lede] if lede is not None else []), *(b for _, bs in sections for b in bs)]
    cited = dict.fromkeys(source_id for b in shown for source_id in b.cited_source_ids())
    document = explainer.model_dump(mode="json", by_alias=True) | {
        **({"lede": lede.model_dump(mode="json", by_alias=True)} if lede is not None else {}),
        "sections": [payload for payload, _ in sections],
        "sources": [merged.get(source_id) or refs[source_id] for source_id in cited],
    }
    return Explainer.model_validate(document)


def _lede(ledger: ClaimLedger, explainer: Explainer, refs: SourceRefs) -> LedeBlock | None:
    return None if explainer.lede is None else ledger.admit_lede(explainer.lede, refs)


def _section(
    ledger: ClaimLedger, section: ExplainerSection, refs: SourceRefs
) -> tuple[dict[str, Any], list[Block]]:
    payload = section.model_dump(mode="json", by_alias=True)
    if section.state == "EMPTY":
        return payload, []
    blocks = [
        block
        for batch in admission_batches(section.blocks)
        for block in ledger.admit(section.id, batch, refs)
    ]
    if not blocks:
        return payload | {"state": "EMPTY", "blocks": [], "searched": COVERED_NOTE}, []
    return payload | {"blocks": [block.model_dump(mode="json", by_alias=True) for block in blocks]}, blocks
