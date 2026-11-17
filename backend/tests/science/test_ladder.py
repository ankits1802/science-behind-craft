import uuid

from app.research.crafts import CraftRef
from app.science.ladder import ladder_problems, ladder_stage_options, process_ladder

from .golden_process import KUT, PA, PROCESS_ID, RED, STAGE_CLAIMS, golden_records, known_claim, stage_id

KUT_REACTION = uuid.UUID("d9643f49-fefc-5e3a-ad08-a5ae499a4161")
RED_REACTION = uuid.UUID("26229ecd-184c-5adf-86d0-b45c56394f27")
KUT_PASTE = uuid.UUID("6a3e5cb8-ef2e-501f-a7f8-d7d0772d56e4")
MADDER = uuid.UUID("a96fc53e-88ae-5f99-acd3-09346d9a67ea")


def ladder(*stages: str):
    built = process_ladder(golden_records(), block_id="s1.b1", stage_ids=[stage_id(s) for s in stages])
    assert built is not None
    return built


def test_the_offered_stages_are_the_stored_stages_with_a_fact_in_ordinal_order() -> None:
    options = ladder_stage_options(golden_records())
    assert [(option.id, option.ordinal, option.name) for option in options] == [
        (stage_id(KUT), 5, "Kut (iron-black printing)"),
        (stage_id(PA), 6, "Pa (alum mordant printing for red)"),
        (stage_id(RED), 11, "Red dyeing (rang) with madder or alizarin"),
    ]


def test_a_ladder_takes_its_stages_claims_conditions_and_reactions_from_the_stored_rows() -> None:
    built = ladder(RED, KUT)
    assert (built.id, built.process_id, built.craft.slug) == ("s1.b1", PROCESS_ID, "Kutch-Ajrakh")
    kut, red = built.stages
    assert [(stage.ordinal, stage.stage_type, stage.level) for stage in built.stages] == [
        (5, "PRINT", "PROVISIONAL"),
        (11, "DYE", "PROVISIONAL"),
    ]
    assert [sentence.id for stage in built.stages for sentence in stage.sentences] == ["s1.b1.1", "s1.b1.2"]
    assert kut.sentences[0].text == known_claim(STAGE_CLAIMS[KUT]).text
    assert red.sentences[0].text == known_claim(STAGE_CLAIMS[RED]).text
    assert [(c.label, c.stated) for c in kut.conditions] == [
        ("Fermenting the iron paste", "ten to fifteen days")
    ]
    assert [(c.label, c.stated) for c in red.conditions] == [("Red dye bath", "up to four hours")]
    assert (kut.reaction_ids, red.reaction_ids) == ([KUT_REACTION], [RED_REACTION])
    assert [m.material_id for m in kut.materials] == [KUT_PASTE]
    assert [m.material_id for m in red.materials] == [MADDER]
    assert ladder_problems(built, golden_records()) == []


def test_stages_outside_the_stored_rows_build_no_ladder() -> None:
    assert process_ladder(golden_records(), block_id="s1.b1", stage_ids=[uuid.uuid4()]) is None


def test_a_ladder_with_a_stage_not_in_the_stored_rows_is_refused() -> None:
    built = ladder(KUT)
    stranger = uuid.UUID("0f0e0d0c-0b0a-4908-8706-050403020100")
    forged = built.model_copy(update={"stages": [built.stages[0].model_copy(update={"stage_id": stranger})]})
    assert ladder_problems(forged, golden_records()) == [
        f"stage {stranger} is not a stored stage of process {PROCESS_ID}"
    ]


def test_a_ladder_stage_that_states_something_its_claims_do_not_is_refused() -> None:
    built = ladder(KUT)
    stage = built.stages[0]
    sentence = stage.sentences[0].model_copy(update={"text": "Kut is printed at dawn."})
    forged = built.model_copy(update={"stages": [stage.model_copy(update={"sentences": [sentence]})]})
    assert ladder_problems(forged, golden_records()) == [
        f"stage {stage_id(KUT)} sentence s1.b1.1 is not one of its stored claims"
    ]


def test_a_ladder_condition_or_reaction_that_is_not_stored_for_its_stage_is_refused() -> None:
    built = ladder(KUT)
    stage = built.stages[0]
    condition = stage.conditions[0].model_copy(update={"stated": "two weeks or more"})
    forged_stage = stage.model_copy(update={"conditions": [condition], "reaction_ids": [RED_REACTION]})
    forged = built.model_copy(update={"stages": [forged_stage]})
    assert ladder_problems(forged, golden_records()) == [
        f"stage {stage_id(KUT)} condition 'Fermenting the iron paste' is not stored for it",
        f"stage {stage_id(KUT)} reaction {RED_REACTION} is not stored for it",
    ]


def test_a_ladder_for_another_craft_is_refused() -> None:
    other = CraftRef(
        slug="Bagru-Hand-Block-Print", name="Bagru Hand Block Print", path="/crafts/Bagru-Hand-Block-Print"
    )
    forged = ladder(KUT).model_copy(update={"craft": other})
    assert ladder_problems(forged, golden_records()) == [
        "ladder s1.b1 is for Bagru-Hand-Block-Print, not Kutch-Ajrakh"
    ]
