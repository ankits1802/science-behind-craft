from app.services.compose_held import About
from app.services.compose_lab import experiment_lab

from .held import BAGRU, FACTS, cited_claims, claim, delivery_problems, held


def test_a_lab_holds_a_toggle_for_each_choice_the_craft_s_facts_compare() -> None:
    result = experiment_lab(BAGRU, About())
    assert result.composed
    harda, madder, lab = result.components
    assert [part.proposal.kind for part in result.components] == [
        "choice_toggle",
        "choice_toggle",
        "experiment_lab",
    ]
    assert [part.proposal.label for part in (harda, madder, lab)] == [
        "bagru-print/chemistry/what-if-m01",
        "bagru-print/chemistry/what-if-m03",
        "bagru-print/chemistry/what-if-lab",
    ]
    spec = lab.proposal.spec
    assert spec is not None
    assert [(item["key"], item["label"], item["toggle"]["component"]) for item in spec["experiments"]] == [
        ("m01", "Harda", harda.proposal.label),
        ("m03", "Madder", madder.proposal.label),
    ]
    assert delivery_problems(result.components) == []


def test_each_option_is_a_material_cited_by_its_own_facts() -> None:
    harda, madder, _ = experiment_lab(BAGRU, About()).components
    body = madder.proposal
    spec = body.spec
    assert spec is not None
    assert body.units[spec["question"]].text == "Madder or Synthetic alizarin?"
    options = {option["value"]: option for option in spec["options"]}
    assert list(options) == ["m03", "m04"]
    said = {
        value: [body.units[part["unit"]].text for part in option["parts"]]
        for value, option in options.items()
    }
    assert said == {"m03": [FACTS[claim(9)]], "m04": [FACTS[claim(10)]]}
    assert [part["option"] for part in spec["visualParts"]] == ["m03", "m04"]
    assert cited_claims(harda) == {claim(8), claim(11)}


def test_a_lab_about_a_material_opens_on_its_choice_and_one_choice_is_no_lab() -> None:
    madder, *_ = experiment_lab(BAGRU, About(material="M03")).components
    assert madder.proposal.label.endswith("what-if-m03")
    single = tuple(material for material in BAGRU.materials if material.key != "M01")
    refused = experiment_lab(held(materials=single), About())
    assert refused.components == ()
    assert refused.missing[0].startswith(
        "two choices Bagru Print's own facts compare: propose_structure ALTERNATIVE"
    )
