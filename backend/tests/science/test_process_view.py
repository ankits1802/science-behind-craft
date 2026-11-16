import uuid
from dataclasses import replace

import pytest

from app.schemas.science import CraftProcess
from app.science.process_view import craft_process, ordered_claims
from app.science.records import (
    ConditionRecord,
    ProcessRecords,
    ReactionRecord,
    ReadingRecord,
    SpeciesRecord,
)

from ..contracts.golden import dumped, golden_text
from .golden_process import (
    GOLDEN,
    KUT,
    RED,
    STAGE_CLAIMS,
    citation_id,
    claim_id,
    golden_records,
    known_claim,
    stage_id,
)

BHATTI_LONG, BHATTI_SHORT = "seed-1d9afc2d4bdccca4d5b0", "seed-1833e19a424b6f9c5df7"


def with_claims(records: ProcessRecords, *claims: str) -> ProcessRecords:
    known = dict(records.claims)
    known.update({claim_id(c): known_claim(c) for c in claims})
    return replace(records, claims=known)


def stage(process: CraftProcess, ordinal: int):
    return next(s for s in process.processes[0].stages if s.ordinal == ordinal)


def test_the_golden_process_is_assembled_from_stored_records() -> None:
    assert dumped(CraftProcess, craft_process(golden_records())) == golden_text(GOLDEN)


def test_a_stage_whose_claims_are_hidden_shows_no_source_found() -> None:
    records = golden_records()
    hidden = {k: v for k, v in records.claims.items() if k != claim_id(STAGE_CLAIMS[KUT])}
    kut = stage(craft_process(replace(records, claims=hidden)), 5)
    assert (kut.level, kut.claims) == ("UNAVAILABLE", [])


def test_a_reading_whose_citation_is_not_shown_is_left_out() -> None:
    records = golden_records()
    visible = {k: v for k, v in records.claims.items() if k != claim_id("seed-d124d09b6ccdc13459f6")}
    [condition] = stage(craft_process(replace(records, claims=visible)), 5).conditions
    assert [r.stated for r in condition.readings] == ["ten to fifteen days"]
    assert [c.id for c in condition.claims] == [claim_id("seed-ca39189df4e04dcb5a7a")]


def test_a_condition_without_shown_readings_and_a_reaction_without_shown_claims_are_left_out() -> None:
    records = golden_records()
    gone = {claim_id("seed-b14a93745f3a652197c0"), claim_id("seed-bd5ef6022d643b22c6dd")}
    red = stage(
        craft_process(replace(records, claims={k: v for k, v in records.claims.items() if k not in gone})), 11
    )
    assert (red.conditions, red.reactions, red.materials) == ([], [], [])


def test_readings_from_two_sources_far_apart_are_flagged() -> None:
    records = with_claims(golden_records(), BHATTI_LONG, BHATTI_SHORT)
    bath = ConditionRecord(
        owner_id=stage_id(RED),
        key="boiling",
        label="Boiling with alizarin",
        quantity="DURATION",
        readings=(
            ReadingRecord(
                claim_id(BHATTI_SHORT), str(citation_id(BHATTI_SHORT, 2)), "about three hours", 3, 3, "hour"
            ),
            ReadingRecord(
                claim_id(BHATTI_LONG), str(citation_id(BHATTI_LONG, 0)), "five to six hours", 5, 6, "hour"
            ),
        ),
    )
    red = stage(craft_process(replace(records, conditions=(*records.conditions, bath))), 11)
    boiling = next(c for c in red.conditions if c.id.endswith(".boiling"))
    assert [(r.min, r.max) for r in boiling.readings] == [(5.0, 6.0), (3.0, 3.0)]
    assert boiling.sources_differ is True


def test_a_temperature_outside_the_dye_envelope_is_shown_with_its_status() -> None:
    records = golden_records()
    hot = ConditionRecord(
        owner_id=stage_id(RED),
        key="temperature",
        label="Dye bath",
        quantity="TEMPERATURE",
        readings=(
            ReadingRecord(
                claim_id(STAGE_CLAIMS[RED]),
                str(citation_id(STAGE_CLAIMS[RED], 1)),
                "up to four hours",
                None,
                230,
                "degF",
            ),
        ),
    )
    red = stage(craft_process(replace(records, conditions=(*records.conditions, hot))), 11)
    temperature = next(c for c in red.conditions if c.quantity == "TEMPERATURE")
    reading = temperature.readings[0]
    assert (reading.max, reading.envelope.status, reading.envelope.max) == (110.0, "OUTSIDE", 100.0)
    assert [c.quantity for c in red.conditions] == ["TEMPERATURE", "DURATION"]


def unbalanced(records: ProcessRecords, **changes: object) -> ProcessRecords:
    claim = STAGE_CLAIMS[KUT]
    reaction = ReactionRecord(
        id=uuid.uuid5(uuid.NAMESPACE_URL, "test-process/unbalanced"),
        stage_id=stage_id(KUT),
        ordinal=2,
        kind="REDOX",
        label="Water to peroxide",
        species=(SpeciesRecord("REACTANT", "H2O", None, None), SpeciesRecord("PRODUCT", "H2O2", None, None)),
        balanced=False,
        coefficients=None,
        checker_version=None,
        delta_h=None,
        citations=((claim_id(claim), str(citation_id(claim, 0))),),
    )
    return replace(records, reactions=(*records.reactions, replace(reaction, **changes)))


def test_an_equation_that_does_not_balance_is_capped_at_hypothesis() -> None:
    kut = stage(craft_process(unbalanced(golden_records())), 5)
    peroxide = kut.reactions[1]
    assert (peroxide.equation, peroxide.level, peroxide.level_reason) == (
        "H2O -> H2O2",
        "HYPOTHESIS",
        "unbalanced",
    )
    assert [s.coefficient for s in peroxide.species] == [None, None]


def test_a_balanced_row_without_coefficients_fails_loudly() -> None:
    with pytest.raises(ValueError, match="no coefficient for each species"):
        craft_process(unbalanced(golden_records(), balanced=True, checker_version="balance/v1"))


def test_delta_h_is_shown_only_when_its_claim_is_shown() -> None:
    shown_claim = claim_id(STAGE_CLAIMS[KUT])
    kut = stage(craft_process(unbalanced(golden_records(), delta_h=(-12.5, shown_claim))), 5)
    assert (kut.reactions[1].delta_h.kj_per_mol, kut.reactions[1].delta_h.claim_id) == (-12.5, shown_claim)
    elsewhere = stage(craft_process(unbalanced(golden_records(), delta_h=(-12.5, uuid.uuid4()))), 5)
    assert elsewhere.reactions[1].delta_h is None


def test_a_cited_source_that_was_not_loaded_fails_loudly() -> None:
    with pytest.raises(ValueError, match="were not loaded"):
        craft_process(replace(golden_records(), sources={}))


def test_claims_are_ordered_by_level_then_text() -> None:
    claims = [known_claim("seed-ca39189df4e04dcb5a7a"), known_claim("seed-e1a28b32e2c7416ebed3")]
    hypothesis = replace(known_claim("seed-d124d09b6ccdc13459f6"), level="HYPOTHESIS")
    ordered = ordered_claims([hypothesis, *claims, claims[0]])
    assert [c.text[:12] for c in ordered] == ["Ajrakh colou", "Kut is made ", "Scrap iron, "]
