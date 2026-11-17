import uuid
from collections.abc import Sequence
from typing import Any

import pytest

from app.research.blocks import ExplainerSentence, ProseBlock
from app.research.citations import SourceRef
from app.research.craft_compare import CraftFacts, SharedTerm
from app.research.crafts import CraftRef
from app.research.offered_facts import STORED_CLAIM, OfferedFact
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec
from app.research.shared_science import TermCraftOffer, TermOffer
from app.services import block_builders
from app.services.answer_events import CitedClaims
from app.services.block_builders import BLOCK_BUILDERS, BlockBuilders
from app.services.builder_interface import BuildAsk, BuilderTools
from app.services.craft_compare import CompareOffers
from app.services.learning_builders import (
    CONCEPT_GRAPH_SECTION_NODES,
    CompareBuilder,
    ConceptGraphBuilder,
    section_term_keys,
)
from app.services.shared_concepts import TermOffers

AJRAKH = CraftRef(slug="Kutch-Ajrakh", name="Kutch Ajrakh", path="/crafts/Kutch-Ajrakh")
BAGRU = CraftRef(slug="Bagru-Print", name="Bagru Print", path="/crafts/Bagru-Print")
TOOLS = BuilderTools(sessions=None, live=None, plan_model=None, compose_model=None)
CITED_SOURCE = "s-cited"
BAGRU_SOURCE = "s-bagru"


def source(source_id: str) -> SourceRef:
    return SourceRef(
        id=source_id,
        kind="GI_JOURNAL",
        title=source_id,
        authors=[],
        year=None,
        doi=None,
        url=None,
        publisher=None,
        licence=None,
        attribution=None,
        reliability="A",
    )


def sentence(
    sentence_id: str, text: str, claim: str, terms: Sequence[tuple[str, str]] = (), src: str = CITED_SOURCE
) -> Any:
    return ExplainerSentence.model_validate(
        {
            "id": sentence_id,
            "text": text,
            "level": "PROVISIONAL",
            "citations": [
                {
                    "id": f"cite-{claim}",
                    "claimId": claim,
                    "sourceId": src,
                    "quote": text,
                    "locator": None,
                    "context": None,
                    "evidence": "QUOTED",
                    "level": "PROVISIONAL",
                }
            ],
            "translated": False,
            "terms": [{"text": shown, "termKey": key} for shown, key in terms],
        }
    )


def prose() -> ProseBlock:
    return ProseBlock(
        id="s3.b1",
        kind="prose",
        version=1,
        reuse=None,
        sentences=[
            sentence(
                "s3.b1.1", "Alum fastens the madder red.", "c1", [("Alum", "alum"), ("madder", "madder")]
            ),
            sentence(
                "s3.b1.2", "Indigo and alum are both used.", "c2", [("Indigo", "indigo"), ("alum", "alum")]
            ),
        ],
    )


def ask(
    discipline: str = "MATERIALS", *, craft: CraftRef | None = AJRAKH, compared: tuple[CraftRef, ...] = ()
) -> BuildAsk:
    request = PlanRequest(
        question="How do Ajrakh and Bagru use alum?", mode="HYBRID", craft=craft, compared=compared
    )
    spec = SectionSpec(id="s3", discipline=discipline, title="Materials", order=3)
    cited = CitedClaims(sources={CITED_SOURCE: source(CITED_SOURCE).model_dump(mode="json", by_alias=True)})
    return BuildAsk(uuid.UUID(int=3), spec, request, (prose(),), cited)


def offered(claim: str, text: str, facet: str, src: str, concept: uuid.UUID | None = None) -> OfferedFact:
    shown = sentence(f"offered.{claim}", text, claim, src=src)
    return OfferedFact(
        sentence=shown, rank=(STORED_CLAIM, 2, 0, -1, text, claim), facet=facet, concept_id=concept
    )


class CompareLoad:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[CraftRef, ...], tuple[str, ...]]] = []

    async def __call__(self, crafts: Sequence[CraftRef], facets: Sequence[str]) -> CompareOffers:
        self.calls.append((tuple(crafts), tuple(facets)))
        return CompareOffers(
            crafts=(
                CraftFacts(
                    craft=AJRAKH, facts=(offered("a1", "Alum is a mordant.", "MATERIALS", CITED_SOURCE),)
                ),
                CraftFacts(
                    craft=BAGRU, facts=(offered("b1", "Alum fixes colour.", "MATERIALS", BAGRU_SOURCE),)
                ),
            ),
            terms=(SharedTerm(key="alum", label="Alum", surfaces=("Alum",)),),
            sources={CITED_SOURCE: source(CITED_SOURCE), BAGRU_SOURCE: source(BAGRU_SOURCE)},
        )


class GraphLoad:
    def __init__(self, count: int = 2) -> None:
        self.count = count
        self.calls: list[tuple[tuple[str, ...], CraftRef]] = []

    async def __call__(self, keys: Sequence[str], craft: CraftRef) -> TermOffers:
        self.calls.append((tuple(keys), craft))
        offers = tuple(self._offer(n) for n in range(self.count))
        return TermOffers(
            offers=offers, sources={CITED_SOURCE: source(CITED_SOURCE), BAGRU_SOURCE: source(BAGRU_SOURCE)}
        )

    def _offer(self, n: int) -> TermOffer:
        label = f"Term{n}"
        ours, theirs = uuid.UUID(int=10 + n), uuid.UUID(int=100 + n)
        return TermOffer(
            key=f"term{n}",
            label=label,
            surfaces=(label,),
            crafts=(
                TermCraftOffer(
                    BAGRU,
                    (theirs,),
                    (offered(f"b{n}", f"{label} in Bagru.", "MATERIALS", BAGRU_SOURCE, theirs),),
                ),
                TermCraftOffer(
                    AJRAKH,
                    (ours,),
                    (offered(f"a{n}", f"{label} in Ajrakh.", "MATERIALS", CITED_SOURCE, ours),),
                ),
            ),
        )


async def test_a_question_about_one_craft_gets_no_comparison() -> None:
    load = CompareLoad()
    built = await CompareBuilder(TOOLS, offers=load).build(ask())
    assert (built.blocks, load.calls) == ((), [])


async def test_a_comparison_sets_the_compared_crafts_side_by_side_on_the_section_s_field() -> None:
    load = CompareLoad()
    built = await CompareBuilder(TOOLS, offers=load).build(ask(compared=(BAGRU,)))
    assert load.calls == [((AJRAKH, BAGRU), ("MATERIALS",))]
    (block,) = built.blocks
    assert (block.kind, block.id, [c.slug for c in block.crafts]) == (
        "compare",
        "s3.compare",
        [AJRAKH.slug, BAGRU.slug],
    )
    assert [(row.facet, row.term.key if row.term else None) for row in block.rows] == [("MATERIALS", "alum")]
    assert set(built.sources) == {BAGRU_SOURCE}


def test_the_terms_a_section_marks_are_read_in_order_of_first_mention() -> None:
    assert section_term_keys([prose()]) == ["alum", "madder", "indigo"]


async def test_the_concept_graph_shows_the_section_s_shared_terms_around_the_answer_s_craft() -> None:
    load = GraphLoad(count=CONCEPT_GRAPH_SECTION_NODES + 2)
    built = await ConceptGraphBuilder(TOOLS, offers=load).build(ask("CHEMISTRY"))
    assert load.calls == [(("alum", "madder", "indigo"), AJRAKH)]
    (block,) = built.blocks
    assert block.focus == AJRAKH and len(block.nodes) == CONCEPT_GRAPH_SECTION_NODES
    assert all(node.crafts[0].craft == AJRAKH for node in block.nodes)
    assert block.nodes[0].crafts[0].sentence.id == "s3.shared.term0.1"
    assert set(built.sources) == {BAGRU_SOURCE}


async def test_an_answer_for_any_craft_gets_no_concept_graph() -> None:
    load = GraphLoad()
    built = await ConceptGraphBuilder(TOOLS, offers=load).build(ask("CHEMISTRY", craft=None))
    assert (built.blocks, load.calls) == ((), [])


def test_comparisons_and_shared_concepts_are_rebuilt_on_reuse_and_never_stored() -> None:
    entries = {entry.kind: entry for entry in BLOCK_BUILDERS}
    assert entries["compare"].rebuilt_on_reuse and entries["concept_graph"].rebuilt_on_reuse
    assert "CHEMISTRY" in entries["concept_graph"].disciplines and "HISTORY" in entries["compare"].disciplines


async def test_a_built_comparison_passes_the_registry_s_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    compare = next(entry for entry in BLOCK_BUILDERS if entry.kind == "compare")
    monkeypatch.setattr(block_builders, "BUILT_BLOCK_KINDS", (*block_builders.BUILT_BLOCK_KINDS, "compare"))
    builders = BlockBuilders([(compare, CompareBuilder(TOOLS, offers=CompareLoad()))])
    added = await builders.added(ask(compared=(BAGRU,)))
    assert [block.kind for block in added.blocks] == ["compare"]
    assert set(added.sources) == {CITED_SOURCE, BAGRU_SOURCE}
