import dataclasses
import uuid

from app.research.blocks_matter import ReactionPlayerBlock
from app.science.reaction_player import REACTION_STEPS_MAX, reaction_player, reaction_player_problems

from ..contracts.golden import golden_json
from .golden_process import GOLDEN, golden_records

KUT_STAGE = uuid.UUID("5ced8309-b0f4-571a-8482-4223d1d4fccc")
RED_STAGE = uuid.UUID("eb895bd5-83a3-511a-9e64-ba7e452afea8")
IRON_ACETATE = uuid.UUID("d9643f49-fefc-5e3a-ad08-a5ae499a4161")
ALIZARIN_LAKE = uuid.UUID("26229ecd-184c-5adf-86d0-b45c56394f27")


def golden_reactions() -> dict[str, dict]:
    stages = [stage for process in golden_json(GOLDEN)["processes"] for stage in process["stages"]]
    return {reaction["id"]: reaction for stage in stages for reaction in stage["reactions"]}


def player() -> ReactionPlayerBlock:
    block = reaction_player(golden_records(), block_id="s4.b2")
    assert block is not None
    return block


def test_the_player_plays_the_stored_reactions_in_process_order() -> None:
    steps = player().steps
    assert [(step.stage_id, step.reaction_id) for step in steps] == [
        (KUT_STAGE, IRON_ACETATE),
        (RED_STAGE, ALIZARIN_LAKE),
    ]
    assert [step.equation for step in steps] == ["Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2", None]
    assert [(step.balanced, step.level) for step in steps] == [(True, "PROVISIONAL"), (False, "PROVISIONAL")]


def test_each_step_carries_the_process_tab_s_values_and_citations() -> None:
    golden = golden_reactions()
    for step in player().steps:
        row = golden[str(step.reaction_id)]
        assert (step.kind, step.label, step.equation, step.balanced, step.level) == (
            row["kind"],
            row["label"],
            row["equation"],
            row["balanced"],
            row["level"],
        )
        assert [s.model_dump(mode="json", by_alias=True) for s in step.species] == row["species"]
        assert [c.id for c in step.citations] == [
            c["id"] for claim in row["claims"] for c in claim["citations"]
        ]


def test_a_player_built_from_the_rows_matches_them() -> None:
    assert reaction_player_problems(player(), golden_records()) == []


def test_a_reaction_not_in_the_stored_rows_is_refused() -> None:
    block = player()
    foreign = block.steps[0].model_copy(update={"reaction_id": uuid.UUID(int=99)})
    problems = reaction_player_problems(block.model_copy(update={"steps": [foreign]}), golden_records())
    assert problems == [f"reaction {uuid.UUID(int=99)} is not a stored reaction of Kutch-Ajrakh"]


def test_a_step_that_changed_a_stored_value_or_cites_another_passage_is_refused() -> None:
    block = player()
    relabelled = block.steps[0].model_copy(update={"label": "Iron rusting"})
    other = block.steps[1].citations[0]
    recited = block.steps[0].model_copy(update={"citations": [*block.steps[0].citations, other]})
    problems = reaction_player_problems(
        block.model_copy(update={"steps": [relabelled, recited]}), golden_records()
    )
    assert problems == [
        f"reaction {IRON_ACETATE} does not match its stored row",
        f"reaction {IRON_ACETATE} cites a passage that is not linked to it",
    ]


def test_a_craft_without_shown_reactions_has_no_player() -> None:
    records = dataclasses.replace(golden_records(), reactions=())
    assert reaction_player(records, block_id="s4.b2") is None


def test_past_the_cap_the_reactions_the_section_cites_are_kept_in_process_order() -> None:
    records = golden_records()
    iron, lake = records.reactions
    copies = tuple(
        dataclasses.replace(iron, id=uuid.UUID(int=n), label=f"Iron step {n:02d}", ordinal=n)
        for n in range(1, REACTION_STEPS_MAX + 1)
    )
    crowded = dataclasses.replace(records, reactions=(*copies, lake))
    plain = reaction_player(crowded, block_id="s4.b2")
    assert [step.reaction_id for step in plain.steps] == [uuid.UUID(int=n) for n in range(1, 9)]
    alizarin_claim = lake.citations[0][0]
    cited = reaction_player(crowded, block_id="s4.b2", cited_claim_ids={str(alizarin_claim)})
    assert [step.reaction_id for step in cited.steps] == [
        *(uuid.UUID(int=n) for n in range(1, 8)),
        ALIZARIN_LAKE,
    ]
