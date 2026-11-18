import asyncio
import dataclasses
from collections import Counter
from typing import Any

import pytest

from app.composer.composer import ModelComposer
from app.core.errors import ExternalFailure
from app.research.quiz import explainer_quiz
from app.services import answer_sections
from app.services.answer_sections import SECTION_STOPPED_NOTE
from app.services.block_builders import BLOCK_BUILDERS, BlockBuilders
from app.services.builder_interface import BuildAsk, Built
from app.services.claim_ledger import ONCE_PER_ANSWER_KINDS
from app.services.stored_fields import fields_held

from ..composer.fixtures import PLAN, pack, section_reply
from ..science.golden_process import golden_records
from .fakes import FakeResearch
from .owner_fixtures import OWNER_UNDERSTOOD, AlwaysReply, GoldenBuilder, curated_ajrakh, golden_builders
from .owner_runs import answered, kinds, owner, seeded_matter

INTERACTIVE = (
    "process_ladder",
    "reaction_player",
    "material_card",
    "molecule_3d",
    "timeline_map",
    "region_story",
    "zoom_story",
    "what_if",
    "market_gi",
    "supply_map",
    "seasons",
    "concept_graph",
    "simulation",
    "expert_view",
)
ONCE = (
    "process_ladder",
    "reaction_player",
    "region_story",
    "seasons",
    "supply_map",
    "zoom_story",
    "simulation",
    "material_card",
    "molecule_3d",
    "concept_graph",
)
PER_FIELD = ("timeline_map", "what_if")
BALANCED_SEED = {"Scrap iron dissolving into iron acetate"}
TOGETHER_WAIT_SECONDS = 1.0


@pytest.fixture
def seed_matter(monkeypatch: pytest.MonkeyPatch) -> None:
    seeded_matter(monkeypatch)


def first_curated(explainer: Any, discipline: str) -> Any:
    (section,) = [section for section in explainer.sections if section.discipline == discipline]
    return next(block for block in section.blocks if block.kind == "prose")


def fields_of(kind: str) -> frozenset[str]:
    return next(entry.disciplines for entry in BLOCK_BUILDERS if entry.kind == kind)


async def test_the_owner_s_expert_question_builds_every_piece_its_claims_and_rows_support(
    seed_matter: None,
) -> None:
    explainer = await answered(owner())
    built = kinds(explainer)
    shown = {section.discipline for section in explainer.sections}
    assert [kind for kind in INTERACTIVE if not built[kind]] == []
    assert {kind: built[kind] for kind in ONCE} == dict.fromkeys(ONCE, 1)
    assert all(1 <= built[kind] <= len(fields_of(kind) & shown) for kind in PER_FIELD)


async def test_the_owner_s_answer_shows_one_market_card_per_craft(seed_matter: None) -> None:
    explainer = await answered(owner())
    markets = Counter(b.craft.slug for s in explainer.sections for b in s.blocks if b.kind == "market_gi")
    assert markets == {"Kutch-Ajrakh": 1}


async def test_the_owner_s_question_leads_with_how_ajrakh_works_and_covers_every_stored_field(
    seed_matter: None,
) -> None:
    curated = curated_ajrakh()
    explainer = await answered(owner())
    held = [d for d in fields_held(curated.claim_disciplines) if d not in OWNER_UNDERSTOOD["disciplines"]]
    assert [s.discipline for s in explainer.sections][:5] == [
        "PROCESS",
        "CHEMISTRY",
        "HISTORY",
        "GEOGRAPHY",
        "ECONOMICS",
    ]
    assert {s.discipline for s in explainer.sections} >= {*OWNER_UNDERSTOOD["disciplines"], *held}
    assert set(held) == {"MATERIALS", "BOTANY"}


async def test_curated_sections_are_the_floor_research_adds_to_at_expert(seed_matter: None) -> None:
    curated = curated_ajrakh()
    run = owner()
    explainer = await answered(run)
    pieces = {piece.facet: piece for piece in curated.pieces}
    for discipline in ("CHEMISTRY", "HISTORY", "GEOGRAPHY", "ECONOMICS", "DESIGN", "PROCESS"):
        prose = first_curated(explainer, discipline)
        assert prose.reuse is not None and prose.reuse.piece_id == pieces[discipline].id
        assert prose.reuse.stored_at == curated.curated_at
    researched = {request.focus for request in run.pipeline.research.requests}
    assert {"CHEMISTRY", "HISTORY", "GEOGRAPHY", "ECONOMICS", "DESIGN", "PROCESS"} <= researched
    (process,) = [section for section in explainer.sections if section.discipline == "PROCESS"]
    assert [block.kind for block in process.blocks][:2] == ["process_ladder", "prose"]


async def test_a_floor_whose_research_composes_nothing_new_is_not_researched_again(seed_matter: None) -> None:
    run = owner()
    quiet = FakeResearch(pack=pack(plan=PLAN.model_copy(update={"queries": []})))
    composer = ModelComposer(model=AlwaysReply(section_reply())).compose
    run = dataclasses.replace(
        run, pipeline=dataclasses.replace(run.pipeline, research=quiet, compose=composer)
    )
    explainer = await answered(run)
    floors = {piece.facet for piece in curated_ajrakh().pieces}
    fresh = {request.focus for request in quiet.requests if request.fresh}
    assert fresh and not fresh & floors
    assert all(section.blocks for section in explainer.sections if section.discipline in floors)


async def test_the_reaction_player_plays_the_stored_seed_reactions_with_their_equations(
    seed_matter: None,
) -> None:
    explainer = await answered(owner())
    (player,) = [b for s in explainer.sections for b in s.blocks if b.kind == "reaction_player"]
    balanced = {step.label for step in player.steps if step.balanced}
    assert balanced >= BALANCED_SEED
    assert len(player.steps) == len(golden_records().reactions)


async def test_every_builder_is_asked_for_its_fields_and_a_craft_level_one_once(seed_matter: None) -> None:
    run = owner()
    explainer = await answered(run)
    shown = {section.discipline for section in explainer.sections}
    asked_for = {kind: [d for d, _ in builder.asked] for kind, builder in run.builders.items()}
    for kind, fields in asked_for.items():
        if kind in ONCE_PER_ANSWER_KINDS:
            assert len(fields) == 1 and set(fields) <= fields_of(kind), kind
        else:
            assert set(fields) == fields_of(kind) & shown, kind


async def test_the_kept_pieces_hold_the_floor_and_what_was_built_on_it_beside_the_curated_ones(
    seed_matter: None,
) -> None:
    run = owner()
    await answered(run)
    ((_, depth, sections),) = run.pieces.kept
    kept = {section.facet: [block.kind for block in section.blocks] for section in sections}
    assert depth == "EXPERT"
    assert kept["PROCESS"][:2] == ["process_ladder", "prose"]
    assert "reaction_player" in kept["CHEMISTRY"]
    assert all(block.reuse is None for section in sections for block in section.blocks)
    curated = [piece for piece in run.pieces.pieces if piece.created_from_answer_id is None]
    assert curated and all(piece.superseded_by_id is None for piece in curated)


async def test_a_quiz_is_built_from_the_owner_s_answer(seed_matter: None) -> None:
    explainer = await answered(owner())
    visible = frozenset(c.claim_id for s in explainer.sections for b in s.blocks for c in b.citations())
    quiz = explainer_quiz(explainer, visible_claim_ids=visible)
    assert quiz is not None and len(quiz.quiz.questions) >= 3


async def test_a_curated_section_that_fails_to_send_stops_alone(
    seed_matter: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent = answer_sections.floor_sent

    async def failing(spec: Any, floor: Any, **options: Any) -> Any:
        if spec.discipline == "CHEMISTRY":
            raise ExternalFailure("translation is down", kind="unavailable", service="translation")
        return await sent(spec, floor, **options)

    monkeypatch.setattr(answer_sections, "floor_sent", failing)
    explainer = await answered(owner())
    (chemistry,) = [s for s in explainer.sections if s.discipline == "CHEMISTRY"]
    assert (chemistry.blocks, chemistry.searched) == ([], SECTION_STOPPED_NOTE)
    assert sum(1 for s in explainer.sections if s.blocks) == len(explainer.sections) - 1


async def test_at_detailed_curated_sections_are_reused_and_still_enriched(seed_matter: None) -> None:
    run = owner()
    explainer = await answered(run, "DETAILED")
    reused = [s for s in explainer.sections if any(b.reuse for b in s.blocks)]
    assert reused
    assert all(
        request.focus not in {s.discipline for s in reused} for request in run.pipeline.research.requests
    )
    built = kinds(explainer)
    assert built["reaction_player"] == 1 and built["process_ladder"] == 1
    marked = [
        t.term_key
        for s in reused
        for b in s.blocks
        for sentence in b.cited_sentences()
        for t in getattr(sentence, "terms", [])
    ]
    assert "alum" in marked


async def test_below_expert_reuse_asks_no_generated_explainer_and_no_expert_panel(seed_matter: None) -> None:
    run = owner()
    await answered(run, "DETAILED")
    assert (run.builders["simulation"].asked, run.builders["expert_view"].asked) == ([], [])


@dataclasses.dataclass
class TogetherBuilder:
    inner: GoldenBuilder
    started: list[str] = dataclasses.field(default_factory=list)
    together: asyncio.Event = dataclasses.field(default_factory=asyncio.Event)

    async def build(self, ask: BuildAsk) -> Built:
        self.started.append(ask.section.id)
        if len(self.started) > 1:
            self.together.set()
        async with asyncio.timeout(TOGETHER_WAIT_SECONDS):
            await self.together.wait()
        return await self.inner.build(ask)


async def test_reused_sections_run_their_builders_together(seed_matter: None) -> None:
    _, made = golden_builders(("measure",))
    entry = next(entry for entry in BLOCK_BUILDERS if entry.kind == "measure")
    run = owner()
    together = TogetherBuilder(made["measure"])
    pipeline = dataclasses.replace(run.pipeline, builders=BlockBuilders([(entry, together)]))
    explainer = await answered(dataclasses.replace(run, pipeline=pipeline), "DETAILED")
    measured = [s.discipline for s in explainer.sections if any(b.kind == "measure" for b in s.blocks)]
    assert len(together.started) > 1
    assert measured == [s.discipline for s in explainer.sections]
