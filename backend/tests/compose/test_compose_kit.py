from app.research.art_kit import PASTE_FORMS
from app.services.compose_held import CraftHeld, HeldAfter, HeldFact, HeldStage
from app.services.compose_kit import PRINTED, stage_scene
from app.services.compose_parts import UnitBook

from .held import BAGRU, claim, held

VAT = claim(20)
FIRE = claim(21)
RINSE = claim(22)
SAID = {
    VAT: "The cloth is lowered into an indigo vat sunk in the ground.",
    FIRE: "The vat is warmed over a wood fire through the night.",
    RINSE: "The cloth is rinsed in running water from the canal.",
}


def craft_with(stage: HeldStage) -> CraftHeld:
    facts = {**BAGRU.facts, **{key: HeldFact(key, text) for key, text in SAID.items()}}
    return held(facts=facts, stages=(*BAGRU.stages, stage))


def test_a_vessel_the_facts_name_is_drawn_alone_and_still_when_no_colour_after_is_recorded() -> None:
    stage = HeldStage("S09", "Indigo dyeing", "DYE", (VAT,))
    book = UnitBook()
    assert stage_scene(craft_with(stage), stage, book) == {
        "parts": [{"part": "bath", "vessel": "vat", "label": "u0001"}]
    }
    assert (book.units()["u0001"].text, book.units()["u0001"].claim_ids) == ("Indigo dyeing", [VAT])


def test_the_heat_and_the_water_the_facts_name_are_drawn_labelled_by_the_sentence_that_names_them() -> None:
    after = HeldAfter("Blue", ("blue",), VAT, ("--dye-indigo",))
    stage = HeldStage("S09", "Indigo dyeing", "DYE", (VAT, FIRE, RINSE), after=after)
    book = UnitBook()
    scene = stage_scene(craft_with(stage), stage, book)
    assert scene is not None
    assert [
        (part["part"], part.get("vessel"), part.get("source"), part.get("form")) for part in scene["parts"]
    ] == [
        ("bath", "vat", None, None),
        ("heat", None, "fire", None),
        ("water", None, None, "running"),
    ]
    assert scene["parts"][0]["piece"] == "--dye-indigo" and scene["motion"] == "dip"
    labels = [book.units()[part["label"]] for part in scene["parts"]]
    assert [(unit.text, unit.claim_ids) for unit in labels] == [
        ("Indigo dyeing", [VAT]),
        (SAID[FIRE], [FIRE]),
        (SAID[RINSE], [RINSE]),
    ]


def test_a_printing_stage_prints_its_material_in_its_recorded_colour_and_a_scene_holds_three_parts_at_most() -> (
    None
):
    assert PRINTED in PASTE_FORMS
    stage = HeldStage(
        "S09",
        "Printing",
        "PRINT",
        (VAT, FIRE, RINSE),
        ("M05",),
        HeldAfter("Blue", ("blue",), VAT, ("--dye-indigo",)),
    )
    scene = stage_scene(craft_with(stage), stage, UnitBook())
    assert scene is not None
    assert [part["part"] for part in scene["parts"]] == ["bath", "paste", "heat"]
    assert scene["parts"][1] == {
        "part": "paste",
        "form": "printed",
        "material": "--dye-kut",
        "label": scene["parts"][1]["label"],
    }


def test_a_stage_whose_facts_name_nothing_the_kit_draws_composes_no_scene() -> None:
    stage = BAGRU.stage("S02")
    assert stage is not None
    book = UnitBook()
    assert stage_scene(BAGRU, stage, book) is None
    assert book.units() == {}
