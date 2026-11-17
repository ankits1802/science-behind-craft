import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from app.research.blocks import ExplainerSentence
from app.research.blocks_learning import COMPARE_ROWS_MAX, CompareBlock
from app.research.citations import SourceRef
from app.research.craft_compare import (
    COMPARE_TERM_ROWS_MAX,
    CraftComparison,
    CraftFacts,
    SharedTerm,
    compare_block,
)
from app.research.crafts import CraftRef
from app.research.offered_facts import PIECE_FIRST, STORED_CLAIM, OfferedFact, fact_rank

AJRAKH = CraftRef(slug="Kutch-Ajrakh", name="Kutch Ajrakh", path="/crafts/Kutch-Ajrakh")
BAGRU = CraftRef(slug="Bagru-Print", name="Bagru Print", path="/crafts/Bagru-Print")
AKOLA = CraftRef(slug="Akola-Print", name="Akola Print", path="/crafts/Akola-Print")
ALUM = SharedTerm(key="alum", label="Alum", surfaces=("Alum", "fitkari"))
SOURCES = {
    "a": SourceRef(
        id="a",
        kind="GI_JOURNAL",
        title="GI Journal",
        authors=[],
        year=2023,
        doi=None,
        url=None,
        publisher=None,
        licence=None,
        attribution=None,
        reliability="A",
    ),
    "b": SourceRef(
        id="b",
        kind="WEB_PAGE",
        title="A page",
        authors=[],
        year=None,
        doi=None,
        url=None,
        publisher=None,
        licence=None,
        attribution=None,
        reliability="B",
    ),
}


def fact(claim: str, text: str, facet: str, **options: Any) -> OfferedFact:
    level = options.get("level", "PROVISIONAL")
    shown = ExplainerSentence.model_validate(
        {
            "id": f"offered.{claim}",
            "text": text,
            "level": level,
            "citations": [
                {
                    "id": f"cite-{claim}",
                    "claimId": claim,
                    "sourceId": options.get("source", "a"),
                    "quote": text,
                    "locator": None,
                    "context": None,
                    "evidence": "QUOTED",
                    "level": level,
                }
            ],
            "translated": False,
            "terms": [],
        }
    )
    origin = PIECE_FIRST if options.get("piece") else STORED_CLAIM
    return OfferedFact(
        sentence=shown,
        rank=fact_rank(shown, SOURCES, origin=origin),
        facet=facet,
        piece_id=options.get("piece"),
    )


def side(craft: CraftRef, *facts: OfferedFact) -> CraftFacts:
    return CraftFacts(craft=craft, facts=facts)


def shown(block: Any) -> list[tuple[str, str | None, list[str | None]]]:
    return [
        (
            row.facet,
            row.term.key if row.term else None,
            [cell.sentence.citations[0].claim_id if cell else None for cell in row.cells],
        )
        for row in block.rows
    ]


def test_a_facet_with_claims_on_one_side_only_is_not_compared() -> None:
    ajrakh = side(
        AJRAKH,
        fact("a1", "Kutch Ajrakh came from Sindh.", "HISTORY"),
        fact("a2", "Alum is a mordant.", "MATERIALS"),
    )
    bagru = side(BAGRU, fact("b1", "Alum fixes colour.", "MATERIALS"))
    block = compare_block([ajrakh, bagru], [], facets=["MATERIALS", "HISTORY"], block_id="c")
    assert block is not None
    assert shown(block) == [("MATERIALS", None, ["a2", "b1"])]
    assert compare_block([ajrakh, bagru], [], facets=["HISTORY"], block_id="c") is None
    assert compare_block([ajrakh, side(BAGRU)], [ALUM], facets=["MATERIALS"], block_id="c") is None


def test_a_term_row_shows_each_craft_s_claim_naming_the_term_then_the_facet_row_the_rest() -> None:
    ajrakh = side(
        AJRAKH,
        fact("a1", "Red comes from madder.", "MATERIALS"),
        fact("a2", "Alum is a mordant.", "MATERIALS"),
    )
    bagru = side(
        BAGRU, fact("b1", "Alum fixes colour.", "MATERIALS"), fact("b2", "Dabu is a mud resist.", "MATERIALS")
    )
    block = compare_block([ajrakh, bagru], [ALUM], facets=["MATERIALS"], block_id="c")
    assert block is not None
    assert shown(block) == [("MATERIALS", "alum", ["a2", "b1"]), ("MATERIALS", None, ["a1", "b2"])]
    cells = block.rows[0].cells
    assert [cell.sentence.id for cell in cells if cell] == ["c.r1.1", "c.r1.2"]
    assert [[span.text for span in cell.sentence.terms] for cell in cells if cell] == [["Alum"], ["Alum"]]
    assert block.rows[1].cells[0].sentence.terms == []


def test_the_strongest_fact_fills_a_cell() -> None:
    ajrakh = side(
        AJRAKH,
        fact("a1", "Alum came from a weaker page.", "MATERIALS", source="b"),
        fact("a2", "Alum is reviewed as a mordant.", "MATERIALS", level="REVIEWED", source="b"),
        fact("a3", "Alum is a mordant in the GI journal.", "MATERIALS"),
    )
    bagru = side(
        BAGRU, fact("b1", "Alum fixes colour.", "MATERIALS"), fact("b2", "Dabu is a mud resist.", "MATERIALS")
    )
    block = compare_block([ajrakh, bagru], [ALUM], facets=["MATERIALS"], block_id="c")
    assert block is not None
    assert shown(block) == [("MATERIALS", "alum", ["a2", "b1"]), ("MATERIALS", None, ["a3", "b2"])]


def test_a_claim_about_the_term_s_own_concept_speaks_for_a_craft_first() -> None:
    alum_concept = uuid.UUID(int=1)
    about = OfferedFact(
        sentence=fact("a2", "Alum is a mordant.", "MATERIALS").sentence,
        rank=fact("a2", "Alum is a mordant.", "MATERIALS").rank,
        facet="MATERIALS",
        concept_id=alum_concept,
    )
    ajrakh = side(AJRAKH, fact("a1", "Alizarin requires alum to fix.", "MATERIALS"), about)
    bagru = side(BAGRU, fact("b1", "Alum fixes colour.", "MATERIALS"))
    term = SharedTerm(key="alum", label="Alum", surfaces=("Alum",), concept_ids=frozenset({alum_concept}))
    block = compare_block([ajrakh, bagru], [term], facets=["MATERIALS"], block_id="c")
    assert block is not None
    assert shown(block)[0] == ("MATERIALS", "alum", ["a2", "b1"])


def test_no_two_cells_of_a_row_rest_on_one_claim() -> None:
    family = fact("f1", "Alum is used across the family.", "MATERIALS")
    ajrakh = side(AJRAKH, family)
    bagru = side(BAGRU, family, fact("b1", "Alum fixes colour.", "MATERIALS", source="b"))
    block = compare_block([ajrakh, bagru], [ALUM], facets=["MATERIALS"], block_id="c")
    assert block is not None
    assert shown(block) == [("MATERIALS", "alum", ["f1", "b1"])]


def test_a_stored_piece_sentence_leads_its_facet_and_names_its_piece() -> None:
    piece = uuid.UUID(int=9)
    ajrakh = side(
        AJRAKH,
        fact("a1", "Water from the Saran river is soft.", "GEOGRAPHY", level="VERIFIED"),
        fact(
            "p1", "Ajrakh printing got concentrated where soft water was available.", "GEOGRAPHY", piece=piece
        ),
    )
    bagru = side(BAGRU, fact("b1", "Bagru printers came for the water.", "GEOGRAPHY"))
    block = compare_block([ajrakh, bagru], [], facets=["GEOGRAPHY"], block_id="c")
    assert block is not None
    assert [cell.piece_id if cell else None for cell in block.rows[0].cells] == [piece, None]


def test_the_limits_hold() -> None:
    terms = [SharedTerm(key=f"term{n}", label=f"Term{n}", surfaces=(f"Term{n}",)) for n in range(6)]
    ajrakh = side(AJRAKH, *(fact(f"a{n}", f"Term{n} is used here.", "MATERIALS") for n in range(6)))
    bagru = side(BAGRU, *(fact(f"b{n}", f"Term{n} is used there.", "MATERIALS") for n in range(6)))
    block = compare_block([ajrakh, bagru], terms, facets=["MATERIALS"], block_id="c")
    assert block is not None
    assert sum(1 for row in block.rows if row.term) == COMPARE_TERM_ROWS_MAX
    assert (
        len(compare_block([ajrakh, bagru], terms, facets=["MATERIALS"], block_id="c", rows_max=2).rows) == 2
    )
    assert len(block.rows) <= COMPARE_ROWS_MAX
    assert compare_block([ajrakh], terms, facets=["MATERIALS"], block_id="c") is None
    assert compare_block([ajrakh, ajrakh], terms, facets=["MATERIALS"], block_id="c") is None
    five = [side(CraftRef(slug=f"c-{n}", name=f"C {n}", path=f"/crafts/c-{n}")) for n in range(5)]
    assert compare_block(five, terms, facets=["MATERIALS"], block_id="c") is None


def test_a_third_craft_without_a_claim_leaves_its_cell_empty() -> None:
    ajrakh = side(AJRAKH, fact("a1", "Alum is a mordant.", "MATERIALS"))
    bagru = side(BAGRU, fact("b1", "Alum fixes colour.", "MATERIALS"))
    block = compare_block([ajrakh, side(AKOLA), bagru], [ALUM], facets=["MATERIALS"], block_id="c")
    assert block is not None
    assert shown(block) == [("MATERIALS", "alum", ["a1", None, "b1"])]


def test_a_built_comparison_sets_different_crafts_side_by_side() -> None:
    ajrakh = side(AJRAKH, fact("a1", "Alum is a mordant.", "MATERIALS"))
    bagru = side(BAGRU, fact("b1", "Alum fixes colour.", "MATERIALS"))
    block = compare_block([ajrakh, bagru], [ALUM], facets=["MATERIALS"], block_id="c")
    assert block is not None
    payload = block.model_dump(mode="json", by_alias=True)
    payload["crafts"] = [payload["crafts"][0], payload["crafts"][0]]
    with pytest.raises(ValidationError, match="different crafts"):
        CompareBlock.model_validate(payload)


def test_a_comparison_lists_the_sources_it_cites_in_order() -> None:
    ajrakh = side(AJRAKH, fact("a1", "Alum is a mordant.", "MATERIALS", source="b"))
    bagru = side(BAGRU, fact("b1", "Alum fixes colour.", "MATERIALS"))
    block = compare_block([ajrakh, bagru], [ALUM], facets=["MATERIALS"], block_id="compare")
    assert block is not None
    kept = CraftComparison(schema_version=1, comparison=block, sources=[SOURCES["b"], SOURCES["a"]])
    assert [s.id for s in kept.sources] == ["b", "a"]
    with pytest.raises(ValidationError, match="every source it cites once"):
        CraftComparison(schema_version=1, comparison=block, sources=[SOURCES["a"], SOURCES["b"]])
