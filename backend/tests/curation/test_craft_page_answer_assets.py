from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime

import pytest

from app.research.blocks import ExplainerSentence, ProseBlock
from app.research.craft_page import CraftPage, PageClaim
from app.services.chapter_draft import ChapterDraft, Drafted
from app.services.chapter_preview import preview_rows
from app.services.craft_page import craft_page
from app.services.craft_page_answer_assets import (
    AnswerPiece,
    AnswerPieces,
    joining_pieces,
    with_answer_pieces,
)
from app.services.curation_preview import dossier_records

from ..contracts.golden import SHARED
from .import_support import AJRAKH

FAMILY = "Textiles-Based-Craft-Category"
ASKED = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)
A, B, C = (uuid.UUID(int=n) for n in (1, 2, 3))


@dataclass(frozen=True)
class FakeBlock:
    kind: str
    claims: tuple[uuid.UUID, ...]
    id: str = "b"

    def cited_claim_ids(self) -> list[str]:
        return [str(claim) for claim in self.claims]


def piece(
    kind: str, *claims: uuid.UUID, facet: str = "CHEMISTRY", topic: str = "t", at: int = 1
) -> AnswerPiece:
    made = ASKED.replace(day=at)
    return AnswerPiece(uuid.UUID(int=100 + at), FakeBlock(kind, claims), facet, topic, claims, made)  # type: ignore[arg-type]


def drafts(*blocks: FakeBlock) -> list[ChapterDraft]:
    return [ChapterDraft("chem", None, [Drafted(block=block) for block in blocks])]  # type: ignore[arg-type]


def test_a_piece_showing_only_what_the_page_shows_does_not_join() -> None:
    page = drafts(FakeBlock("prose", (A,)))
    assert joining_pieces([piece("prose", A)], page, {A, B}) == []


def test_a_piece_adding_a_claim_the_page_lacks_joins() -> None:
    page = drafts(FakeBlock("prose", (A,)))
    adding = piece("prose", A, B)
    assert joining_pieces([adding], page, {A, B}) == [adding]


def test_a_kind_the_page_rebuilds_from_rows_keeps_the_page_s_own() -> None:
    page = drafts(FakeBlock("reaction_player", (A,)))
    assert joining_pieces([piece("reaction_player", A, B)], page, {A, B}) == []


def test_a_piece_citing_a_claim_the_page_does_not_list_never_joins() -> None:
    assert joining_pieces([piece("prose", C)], drafts(), {A, B}) == []


def test_one_piece_per_slot_the_one_showing_more_claims() -> None:
    narrow, wide = piece("prose", B, at=9), piece("prose", A, B, at=2)
    assert joining_pieces([narrow, wide], drafts(), {A, B}) == [wide]


def golden_claims() -> tuple[CraftPage, list[PageClaim]]:
    records = dossier_records(AJRAKH)
    rows = preview_rows(records, family=FAMILY, inputs=SHARED / "craft.page.inputs.json")
    page = craft_page(records, rows)
    cited = {c.claim_id for chapter in page.chapters for s in chapter.sentences() for c in s.citations}
    cited |= {c.claim_id for s in page.lede for c in s.citations}
    unshown = [claim for claim in page.claims if str(claim.id) not in cited and claim.level != "HYPOTHESIS"]
    return page, unshown


@pytest.fixture(scope="module")
def unshown() -> PageClaim:
    _, claims = golden_claims()
    economics = [claim for claim in claims if claim.discipline == "ECONOMICS"]
    return (economics or claims)[0]


def reader_piece(claim: PageClaim) -> AnswerPiece:
    sentence = ExplainerSentence(
        id="r1.1", text=claim.text, level=claim.level, citations=list(claim.citations), terms=[]
    )
    block = ProseBlock(id="s3.b2", kind="prose", version=1, reuse=None, sentences=[sentence])
    return AnswerPiece(uuid.UUID(int=77), block, claim.discipline, "topic", (claim.id,), ASKED)


def test_a_reader_s_piece_with_something_new_joins_its_chapter_marked_as_a_reader_s(
    unshown: PageClaim,
) -> None:
    records = dossier_records(AJRAKH)
    rows = preview_rows(records, family=FAMILY, inputs=SHARED / "craft.page.inputs.json")
    joined = replace(rows, answers=AnswerPieces((reader_piece(unshown),)))
    page = craft_page(records, joined)
    items = [
        item for chapter in page.chapters for item in chapter.items if item.piece_id == uuid.UUID(int=77)
    ]
    assert len(items) == 1
    (item,) = items
    assert item.origin is not None and item.origin.basis == "READERS"
    assert item.origin.from_question is not None
    assert (item.origin.from_question.text, item.origin.from_question.asked_in) == (None, "2026-11")
    assert item.origin.generated is None
    assert item.block is not None and item.block.id.endswith(".reader-1")


def test_a_piece_of_no_chapter_kind_goes_to_its_facet_s_chapter() -> None:
    sentence_claim = uuid.UUID(int=5)
    block = FakeBlock("prose", (sentence_claim,))
    adding = AnswerPiece(uuid.UUID(int=9), block, "ECONOMICS", "t", (sentence_claim,), ASKED)  # type: ignore[arg-type]
    base = [ChapterDraft("chem", None, []), ChapterDraft("sources", None, [])]
    placed = joining_pieces([adding], base, {sentence_claim})
    assert placed == [adding]
    assert adding.chapter == "market"


def test_the_merge_places_a_new_chapter_between_its_neighbours(unshown: PageClaim) -> None:
    base = [ChapterDraft("glance", None, []), ChapterDraft("sources", None, [])]
    reader = replace(reader_piece(unshown), facet="ECONOMICS")
    placed = with_answer_pieces(base, [reader], {unshown.id})
    assert [draft.key for draft in placed] == ["glance", "market", "sources"]
    assert placed[1].items[0].piece_id == uuid.UUID(int=77)
