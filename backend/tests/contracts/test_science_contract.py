import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.science import (
    CitedClaim,
    ConditionReading,
    CraftProcess,
    ProcessStageView,
    ReactionView,
    StageCondition,
    envelope_status,
    mhchem_equation,
    sources_differ,
)

from .golden import golden_json, reproduces

GOLDEN = "science.process.golden.json"
SOURCE = "d0f53ee9-4b97-5df7-a367-686957bdb7c8"


def claim(level: str = "PROVISIONAL", key: str = "a") -> dict[str, Any]:
    claim_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"claim:{key}"))
    return {
        "id": claim_id,
        "text": f"Claim {key}.",
        "level": level,
        "citations": [
            {
                "id": f"cite-{key}",
                "claimId": claim_id,
                "sourceId": SOURCE,
                "quote": "A quoted passage of the source that is long enough.",
                "locator": "p. 1",
                "context": None,
                "evidence": "QUOTED",
                "level": level,
            }
        ],
    }


def species(role: str, formula: str | None, coefficient: int | None = None) -> dict[str, Any]:
    return {"role": role, "formula": formula, "name": None, "coefficient": coefficient, "compoundId": None}


def reaction(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "kind": "DEHYDROXYLATION",
        "label": "Kaolinite losing its hydroxyl water",
        "species": [
            species("REACTANT", "Al2Si2O5(OH)4", 1),
            species("PRODUCT", "Al2Si2O7", 1),
            species("PRODUCT", "H2O", 2),
        ],
        "balanced": True,
        "equation": "Al2Si2O5(OH)4 -> Al2Si2O7 + 2 H2O",
        "checkerVersion": "balance/v1",
        "conditions": [],
        "deltaH": None,
        "level": "PROVISIONAL",
        "levelReason": None,
        "claims": [claim()],
    }
    body.update(changes)
    return body


def reading(low: float | None, high: float | None, envelope: tuple[str, float | None, float | None]) -> dict:
    status, env_min, env_max = envelope
    return {
        "claimId": claim()["id"],
        "min": low,
        "max": high,
        "stated": "as stated",
        "envelope": {"status": status, "min": env_min, "max": env_max},
    }


def test_the_golden_process_is_reproduced_byte_for_byte() -> None:
    assert reproduces(CraftProcess, GOLDEN)


def test_the_golden_process_carries_both_ajrakh_reactions() -> None:
    process = CraftProcess.model_validate(golden_json(GOLDEN))
    stages = process.processes[0].stages
    assert [stage.ordinal for stage in stages] == [5, 6, 11]
    iron, lake = stages[0].reactions[0], stages[2].reactions[0]
    assert (iron.balanced, iron.equation) == (True, "Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2")
    assert (lake.balanced, lake.equation, lake.level, lake.level_reason) == (False, None, "PROVISIONAL", None)
    assert [source.reliability for source in process.sources] == ["A", "B"]


def test_a_balanced_reaction_uses_the_smallest_integers() -> None:
    doubled = [
        species("REACTANT", "Al2Si2O5(OH)4", 2),
        species("PRODUCT", "Al2Si2O7", 2),
        species("PRODUCT", "H2O", 4),
    ]
    with pytest.raises(ValidationError, match="smallest integer"):
        ReactionView.model_validate(
            reaction(species=doubled, equation="2 Al2Si2O5(OH)4 -> 2 Al2Si2O7 + 4 H2O")
        )


def test_an_unbalanced_reaction_carries_no_coefficients() -> None:
    with pytest.raises(ValidationError, match="carries no coefficients"):
        ReactionView.model_validate(reaction(balanced=False, checkerVersion=None, level="HYPOTHESIS"))


def test_an_unbalanced_equation_caps_its_level_at_hypothesis() -> None:
    bare = [species("REACTANT", "Al2Si2O5(OH)4"), species("PRODUCT", "Al2Si2O7"), species("PRODUCT", "H2O")]
    body = reaction(
        species=bare, balanced=False, checkerVersion=None, equation="Al2Si2O5(OH)4 -> Al2Si2O7 + H2O"
    )
    with pytest.raises(ValidationError, match="is HYPOTHESIS"):
        ReactionView.model_validate(body)
    capped = ReactionView.model_validate({**body, "level": "HYPOTHESIS", "levelReason": "unbalanced"})
    assert (capped.level, capped.level_reason) == ("HYPOTHESIS", "unbalanced")


def test_a_species_only_reaction_has_no_equation_and_keeps_its_level() -> None:
    lake = [
        species("REACTANT", "Al^3+"),
        species("REACTANT", "C14H8O4"),
        {**species("PRODUCT", None), "name": "Lake"},
    ]
    view = ReactionView.model_validate(
        reaction(kind="COMPLEXATION", species=lake, balanced=False, equation=None, checkerVersion=None)
    )
    assert (view.equation, view.level) == (None, "PROVISIONAL")


def test_the_equation_is_built_from_the_species() -> None:
    assert ReactionView.model_validate(reaction()).equation == "Al2Si2O5(OH)4 -> Al2Si2O7 + 2 H2O"
    with pytest.raises(ValidationError, match="not built from its species"):
        ReactionView.model_validate(reaction(equation="Al2Si2O5(OH)4 = Al2Si2O7 + 2 H2O"))


def test_a_derived_reaction_takes_its_weakest_claim() -> None:
    claims = [claim("REVIEWED", "a"), claim("PROVISIONAL", "b")]
    assert ReactionView.model_validate(reaction(claims=claims)).level == "PROVISIONAL"
    with pytest.raises(ValidationError, match="is PROVISIONAL"):
        ReactionView.model_validate(reaction(claims=claims, level="REVIEWED"))


def test_delta_h_is_shown_only_when_a_listed_claim_cites_it() -> None:
    stray = {"kjPerMol": 42.0, "claimId": str(uuid.uuid4())}
    with pytest.raises(ValidationError, match="ΔH"):
        ReactionView.model_validate(reaction(deltaH=stray))


@pytest.mark.parametrize(
    ("quantity", "first", "second", "differ"),
    [
        ("TEMPERATURE", 60.0, 90.0, True),
        ("TEMPERATURE", 60.0, 80.0, False),
        ("PH", 4.0, 4.8, True),
        ("PH", 4.0, 4.6, False),
        ("DURATION", 300.0, 336.0, False),
    ],
)
def test_sources_differ_past_fifteen_percent_or_twenty_five_degrees(
    quantity: str, first: float, second: float, differ: bool
) -> None:
    readings = [ConditionReading.model_validate(reading(v, v, ("NONE", None, None))) for v in (first, second)]
    assert sources_differ(quantity, readings) is differ


def test_a_range_is_compared_by_its_midpoint() -> None:
    ranged = ConditionReading.model_validate(reading(240.0, 360.0, ("NONE", None, None)))

    def against(value: float) -> bool:
        exact = ConditionReading.model_validate(reading(value, value, ("NONE", None, None)))
        return sources_differ("DURATION", [ranged, exact])

    assert (against(260.0), against(345.0), against(360.0)) == (False, False, True)


@pytest.mark.parametrize(
    ("low", "high", "status"),
    [(60.0, 80.0, "WITHIN"), (None, 110.0, "OUTSIDE"), (15.0, None, "OUTSIDE"), (20.0, 100.0, "WITHIN")],
)
def test_the_dye_envelope_of_twenty_to_a_hundred_degrees(
    low: float | None, high: float | None, status: str
) -> None:
    assert envelope_status(low, high, 20.0, 100.0) == status
    assert envelope_status(low, high, None, None) == "NONE"


def test_a_condition_whose_flag_breaks_the_rule_is_refused() -> None:
    body = {
        "id": "stage.temperature",
        "label": "Dye bath",
        "quantity": "TEMPERATURE",
        "unit": "°C",
        "readings": [
            reading(60.0, 60.0, ("WITHIN", 20.0, 100.0)),
            reading(95.0, 95.0, ("WITHIN", 20.0, 100.0)),
        ],
        "sourcesDiffer": False,
        "level": "PROVISIONAL",
        "claims": [claim()],
    }
    with pytest.raises(ValidationError, match="sources-differ"):
        StageCondition.model_validate(body)
    assert StageCondition.model_validate({**body, "sourcesDiffer": True}).sources_differ
    with pytest.raises(ValidationError, match="given in °C"):
        StageCondition.model_validate({**body, "sourcesDiffer": True, "unit": "K"})


def test_a_reading_outside_its_envelope_must_say_so() -> None:
    with pytest.raises(ValidationError, match="is OUTSIDE"):
        ConditionReading.model_validate(reading(None, 110.0, ("WITHIN", 20.0, 100.0)))


def test_a_citation_of_another_claim_is_refused() -> None:
    body = claim()
    body["citations"][0]["claimId"] = str(uuid.uuid4())
    with pytest.raises(ValidationError, match="does not carry claim"):
        CitedClaim.model_validate(body)


def test_a_stage_without_claims_shows_no_source_found() -> None:
    stage = {
        "id": str(uuid.uuid4()),
        "ordinal": 1,
        "name": "Washing",
        "stageType": "WASH",
        "level": "UNAVAILABLE",
        "claims": [],
        "materials": [],
        "conditions": [],
        "reactions": [],
    }
    assert ProcessStageView.model_validate(stage).level == "UNAVAILABLE"
    with pytest.raises(ValidationError, match="is UNAVAILABLE"):
        ProcessStageView.model_validate({**stage, "level": "PROVISIONAL"})


def test_sources_list_the_cited_ones_in_order_of_first_citation() -> None:
    body = golden_json(GOLDEN)
    body["sources"].reverse()
    with pytest.raises(ValidationError, match="order of first citation"):
        CraftProcess.model_validate(body)


def test_stages_rise_by_ordinal() -> None:
    body = golden_json(GOLDEN)
    stages = body["processes"][0]["stages"]
    stages[0], stages[1] = stages[1], stages[0]
    with pytest.raises(ValidationError, match="rising ordinal"):
        CraftProcess.model_validate(body)


def test_mhchem_equation_writes_a_coefficient_only_above_one() -> None:
    view = ReactionView.model_validate(reaction())
    assert mhchem_equation(view.species) == "Al2Si2O5(OH)4 -> Al2Si2O7 + 2 H2O"
