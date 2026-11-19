from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.core.errors import InvalidInput
from app.curation.dossier import Dossier
from app.curation.overview import KeyFact, Overview, OverviewSection, OverviewSentence

from .curated_category_index import CuratedCategoryPage, IndexSentenceRefs
from .curation_overview import LEDE_PART
from .dossier_export_records import StoredCuration, keyed

__all__ = ["DROPPED_SENTENCE_NOTE", "ExportedOverview", "same_curation", "stored_overview"]

DROPPED_SENTENCE_NOTE = (
    "the import's prose validator dropped it, so it is kept as the dossier in git gives it"
)

Part = tuple[str, list[OverviewSentence]]


@dataclass(frozen=True)
class ExportedOverview:
    overview: Overview
    carried: list[str]


def same_curation(stored: StoredCuration, previous: Dossier | None) -> bool:
    page = stored.page
    return (
        previous is not None and previous.version == page.version and previous.curated_at == page.curated_at
    )


def stored_overview(
    stored: StoredCuration, keys: Mapping[uuid.UUID, str], previous: Dossier | None
) -> ExportedOverview:
    page = stored.page
    refs = page.refs() if isinstance(page, CuratedCategoryPage) else {}
    held: list[Part] = [(LEDE_PART, _sentences(stored, page.overview.lede_piece_id, keys, refs))]
    held += [
        (section.discipline, _sentences(stored, section.piece_id, keys, refs))
        for section in page.overview.sections
    ]
    carried: list[str] = []
    if previous is not None and same_curation(stored, previous):
        held = _with_dropped(held, _parts(previous.overview), carried)
    lede = dict(held).get(LEDE_PART, [])
    sections = [
        OverviewSection(discipline=part, sentences=sentences) for part, sentences in held if part != LEDE_PART
    ]
    key_facts = [
        KeyFact(label=fact.label, value=fact.value, claim_ids=keyed(fact.claim_ids, keys))
        for fact in page.overview.key_facts
    ]
    return ExportedOverview(Overview(lede=lede, key_facts=key_facts, sections=sections), carried)


def _sentences(
    stored: StoredCuration,
    piece_id: uuid.UUID | None,
    keys: Mapping[uuid.UUID, str],
    refs: Mapping[str, IndexSentenceRefs],
) -> list[OverviewSentence]:
    if piece_id is None:
        return []
    found = stored.sentences.get(piece_id)
    if found is None:
        raise InvalidInput(f"overview piece {piece_id} of {stored.slug} is not stored")
    sentences = []
    for sentence in found:
        ref = refs.get(sentence.id)
        sentences.append(
            OverviewSentence(
                text=sentence.text,
                claim_ids=keyed(sentence.claim_ids, keys),
                sub_categories=ref.sub_categories if ref else [],
                crafts=ref.crafts if ref else [],
            )
        )
    return sentences


def _parts(overview: Overview) -> list[Part]:
    return [
        (LEDE_PART, list(overview.lede)),
        *((section.discipline, list(section.sentences)) for section in overview.sections),
    ]


def _with_dropped(held: Sequence[Part], earlier: Sequence[Part], carried: list[str]) -> list[Part]:
    shown = dict(held)
    merged = []
    for part, sentences in earlier:
        texts = {sentence.text: sentence for sentence in shown.pop(part, [])}
        if not texts.keys() <= {sentence.text for sentence in sentences}:
            merged.append((part, list(texts.values())))
            continue
        carried += [
            f"overview.{part}.{index}: {DROPPED_SENTENCE_NOTE}"
            for index, sentence in enumerate(sentences)
            if sentence.text not in texts
        ]
        merged.append((part, [texts.get(sentence.text, sentence) for sentence in sentences]))
    return merged + list(shown.items())
