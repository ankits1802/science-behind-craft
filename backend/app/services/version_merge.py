from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.core.errors import InvalidInput
from app.research.citations import SourceRef
from app.research.explainer import EXPLAINER_SCHEMA_VERSION, Explainer, ExplainerSection
from app.research.explainer_versions import (
    IMAGES_KIND,
    ExplainerVersionDocument,
    SectionChange,
    VersionMark,
    version_problems,
)

from .explainer_payload import version_document

__all__ = ["merged_version"]

READY = "READY"


def merged_version(base: ExplainerVersionDocument, follow_up: Explainer) -> ExplainerVersionDocument:
    explainer = base.explainer
    offered = {section.id: section for section in follow_up.sections if section.blocks}
    known = {section.id for section in explainer.sections}
    kept = [_deepened(section, offered.get(section.id)) for section in explainer.sections]
    added = [section for section in follow_up.sections if section.id not in known and section.blocks]
    sections = [*kept, *(_placed(section, len(kept) + n) for n, section in enumerate(added, 1))]
    merged = Explainer(
        schema_version=EXPLAINER_SCHEMA_VERSION,
        answer_id=follow_up.answer_id,
        question=follow_up.question,
        understood=explainer.understood,
        sections=sections,
        sources=_cited_sources(sections, [*follow_up.sources, *explainer.sources]),
        follow_ups=list(follow_up.follow_ups or explainer.follow_ups),
        created_at=follow_up.created_at,
    )
    changes = _changes(explainer, offered, added)
    mark = VersionMark(
        explainer_id=base.mark.explainer_id,
        version=base.mark.version + 1,
        answer_id=follow_up.answer_id,
        based_on=base.mark.version,
        question=follow_up.question,
        changes=changes,
        created_at=follow_up.created_at,
    )
    problems = version_problems(explainer, merged, changes)
    if problems:
        raise InvalidInput(
            f"follow-up {follow_up.answer_id} would break version {mark.version} of explainer "
            f"{mark.explainer_id}: {'; '.join(problems)}"
        )
    return version_document(mark, merged)


def _deepened(section: ExplainerSection, offered: ExplainerSection | None) -> ExplainerSection:
    if offered is None:
        return section
    own = [block for block in section.blocks if block.kind != IMAGES_KIND]
    pictures = [block for block in section.blocks if block.kind == IMAGES_KIND]
    blocks = [*own, *offered.blocks, *pictures]
    return ExplainerSection(**{**dict(section), "state": READY, "searched": None, "blocks": blocks})


def _placed(section: ExplainerSection, order: int) -> ExplainerSection:
    return ExplainerSection(**{**dict(section), "order": order})


def _cited_sources(sections: Sequence[ExplainerSection], known: Sequence[SourceRef]) -> list[SourceRef]:
    by_id = {source.id: source for source in known}
    cited = dict.fromkeys(
        source_id
        for section in sections
        for block in section.blocks
        for source_id in block.cited_source_ids()
    )
    unknown = [source_id for source_id in cited if source_id not in by_id]
    if unknown:
        raise InvalidInput(f"a follow-up cites sources neither version lists: {', '.join(unknown)}")
    return [by_id[source_id] for source_id in cited]


def _changes(
    explainer: Explainer, offered: Mapping[str, ExplainerSection], added: Sequence[ExplainerSection]
) -> list[SectionChange]:
    deepened = [
        SectionChange(
            section_id=section.id,
            change="DEEPENED",
            block_ids=[block.id for block in offered[section.id].blocks],
        )
        for section in explainer.sections
        if section.id in offered
    ]
    return deepened + [
        SectionChange(section_id=section.id, change="ADDED", block_ids=[block.id for block in section.blocks])
        for section in added
    ]
