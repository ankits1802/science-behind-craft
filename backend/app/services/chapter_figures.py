from __future__ import annotations

from collections.abc import Sequence

from app.research.blocks import ExplainerSentence
from app.research.blocks_signature import SignatureBlock
from app.research.vocabulary import FACT_LEVELS, LEVEL_ORDER

from .chapter_context import ChapterContext
from .signature_blocks import signature_block
from .signature_rules import FigureEvidence

__all__ = ["CHEMISTRY_FIGURES", "MAKING_FIGURES", "signature_figures"]

CHEMISTRY_FIGURES = ("indigo_vat", "mordant_bath")
MAKING_FIGURES = ("lost_wax", "firing")
CURATED = "CURATED"


def signature_figures(ctx: ChapterContext, kinds: Sequence[str], chapter: str) -> list[SignatureBlock]:
    evidence = FigureEvidence(
        facts=_ranked_facts(ctx),
        compounds=tuple(ctx.rows.compounds.values()),
        record_sources={
            sid: ref.model_dump(mode="json", by_alias=True) for sid, ref in ctx.rows.record_sources.items()
        },
    )
    figures = []
    for kind in kinds:
        figure = signature_block(kind, evidence, block_id=f"{chapter}.figure-{kind.replace('_', '-')}")
        if figure is not None:
            figures.append(figure)
    return figures


def _ranked_facts(ctx: ChapterContext) -> tuple[ExplainerSentence, ...]:
    own = [claim for claim in ctx.claims.values() if claim.id in ctx.own and claim.level in FACT_LEVELS]
    own.sort(
        key=lambda claim: (
            claim.provenance != CURATED,
            LEVEL_ORDER[claim.level],
            ctx.visible.order.get(claim.id, 0),
        )
    )
    found = [ctx.sentence(claim.id, f"fact.{n}") for n, claim in enumerate(own, start=1)]
    return tuple(sentence for sentence in found if sentence is not None)
