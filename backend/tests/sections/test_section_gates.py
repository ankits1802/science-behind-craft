import uuid
from typing import Any

import pytest

from app.core.errors import ExternalFailure
from app.research.section_proposals import SectionPart, first_refusal
from app.services.knowledge_view import ClaimView
from app.services.section_gates import ShownFacts, faithful_check, section_checks, stale_problem

from ..knowledge_writes.fakes import JUDGE_MODEL, FakeJudge

ALUM = uuid.UUID("5ec70000-0000-4000-8000-000000000001")
MADDER = uuid.UUID("5ec70000-0000-4000-8000-000000000002")
WASH = uuid.UUID("5ec70000-0000-4000-8000-000000000003")
LIME = uuid.UUID("5ec70000-0000-4000-8000-000000000004")
GONE = uuid.UUID("5ec70000-0000-4000-8000-000000000005")
TEXTS = {
    ALUM: "Alum is printed on the cloth before it goes into the madder bath.",
    MADDER: "Madder gives a red colour on cotton.",
    WASH: "The printed cloth is washed in the river after the madder bath.",
    LIME: "Lime is added to the indigo vat.",
}
FIELDS = {ALUM: ("CHEMISTRY",), MADDER: ("CHEMISTRY",), WASH: ("PROCESS", "CHEMISTRY"), LIME: ("PROCESS",)}


def view(claim_id: uuid.UUID, level: str = "PROVISIONAL") -> ClaimView:
    cite = {"id": f"cite-{claim_id}", "quote": TEXTS[claim_id].lower().rstrip(".")}
    return ClaimView(
        id=claim_id, text=TEXTS[claim_id], level=level, concept_type="", concept_id=None, citations=[cite]
    )


def facts(in_field: int = 3, **levels: str) -> ShownFacts:
    views = {claim: view(claim, levels.get(str(claim), "PROVISIONAL")) for claim in TEXTS}
    return ShownFacts(views=views, fields=FIELDS, in_field=in_field)


def part(*sentences: tuple[str, list[uuid.UUID]], field: str = "CHEMISTRY") -> SectionPart:
    return SectionPart.model_validate(
        {
            "field": field,
            "sentences": [{"text": text, "claimIds": [str(c) for c in ids]} for text, ids in sentences],
        }
    )


RESTATED = part(
    (TEXTS[ALUM], [ALUM]),
    (TEXTS[MADDER], [MADDER]),
    (TEXTS[WASH], [WASH]),
)


def checked(found: SectionPart, shown: ShownFacts) -> list[tuple[str, bool]]:
    return [(check.check, check.passed) for check in section_checks(found, shown)]


def test_a_section_resting_on_shown_facts_of_its_field_passes_every_check_before_the_judge() -> None:
    assert checked(RESTATED, facts()) == [
        ("HELD", True),
        ("FIELD", True),
        ("SENTENCES", True),
        ("STATED", True),
    ]


def test_a_fact_the_page_does_not_hold_refuses_the_whole_section_naming_the_sentence() -> None:
    found = part((TEXTS[ALUM], [ALUM]), (TEXTS[MADDER], [MADDER, GONE]), (TEXTS[WASH], [WASH]))
    checks = section_checks(found, facts())
    assert [(check.check, check.passed) for check in checks] == [("HELD", False)]
    assert checks[0].reasons == [f"sentence 2 cites {GONE}, which this page does not hold as a shown fact"]
    assert stale_problem(found, facts()) == checks[0].reasons[0]


def test_a_fact_of_another_field_is_refused_and_one_naming_the_field_among_its_fields_passes() -> None:
    other = part((TEXTS[ALUM], [ALUM]), (TEXTS[MADDER], [MADDER]), (TEXTS[LIME], [LIME]))
    checks = section_checks(other, facts())
    assert [(check.check, check.passed) for check in checks] == [("HELD", True), ("FIELD", False)]
    assert checks[1].reasons == [f"sentence 3 cites {LIME}, a fact of PROCESS, not of CHEMISTRY"]
    secondary = part((TEXTS[ALUM], [ALUM]), (TEXTS[MADDER], [MADDER]), (TEXTS[WASH], [WASH]))
    assert first_refusal(section_checks(secondary, facts())) is None


def test_a_section_shorter_than_its_facts_allow_is_refused_and_a_short_field_says_how_many() -> None:
    two = part((TEXTS[ALUM], [ALUM]), (TEXTS[MADDER], [MADDER]))
    refused = first_refusal(section_checks(two, facts(in_field=5)))
    assert refused is not None and refused.check == "SENTENCES"
    assert refused.reasons == [
        "the section holds 2 sentences, and the 5 facts this page holds in CHEMISTRY need at least 3"
    ]
    allowed = section_checks(two, facts(in_field=2))
    assert first_refusal(allowed) is None
    assert allowed[2].reasons == ["2 sentences, as many as the 2 facts this page holds in CHEMISTRY allow"]
    assert section_checks(RESTATED, facts())[2].reasons == ["3 sentences"]


def test_a_number_its_facts_do_not_state_is_refused_before_any_judge_is_asked() -> None:
    found = part(
        ("Alum is printed on the cloth 2 days before it goes into the madder bath.", [ALUM]),
        (TEXTS[MADDER], [MADDER]),
        (TEXTS[WASH], [WASH]),
    )
    refused = first_refusal(section_checks(found, facts()))
    assert refused is not None and refused.check == "STATED"
    assert refused.reasons[0].startswith("sentence 1 states")


def test_a_hypothesis_is_not_a_fact_a_section_may_rest_on() -> None:
    refused = first_refusal(section_checks(RESTATED, facts(**{str(MADDER): "HYPOTHESIS"})))
    assert refused is not None and refused.check == "STATED"
    assert refused.reasons == ["sentence 2 is not a fact"]


def verdicts(*found: tuple[str, list[str]]) -> dict[str, Any]:
    return {
        "verdicts": [
            {"candidate": ref, "newDetails": details, "specific": True, "coveredBy": [], "reason": "Read."}
            for ref, details in found
        ]
    }


async def test_a_sentence_saying_what_its_facts_do_not_refuses_the_section_with_the_judges_details() -> None:
    found = part(
        ("Alum goes onto the cloth before the madder bath because it fixes the red.", [ALUM, MADDER]),
        (TEXTS[MADDER], [MADDER]),
        ("After the madder bath the printed cloth is washed in the river.", [WASH]),
    )
    judge = FakeJudge(verdicts(("sentence-1", ["alum fixes the red"]), ("sentence-3", [])))
    check = await faithful_check(found, facts(), (judge,))
    assert (check.check, check.passed) == ("FAITHFUL", False)
    assert check.reasons == ["sentence 1 says what its facts do not: alum fixes the red"]
    assert len(judge.calls) == 1 and "sentence-2" not in judge.calls[0]["user"]


async def test_a_judge_that_finds_nothing_new_passes_the_section_and_is_named() -> None:
    found = part(("Madder gives the cotton its red colour.", [MADDER]))
    check = await faithful_check(found, facts(), (FakeJudge(verdicts(("sentence-1", []))),))
    assert (check.passed, check.reasons) == (
        True,
        [f"the judge ({JUDGE_MODEL}) found nothing a sentence says that its facts do not"],
    )


async def test_a_section_that_restates_its_facts_asks_no_judge() -> None:
    judge = FakeJudge()
    check = await faithful_check(RESTATED, facts(), (judge,))
    assert check.passed and judge.calls == []


async def test_without_a_judge_the_check_fails_closed() -> None:
    found = part(("Madder gives the cotton its red colour.", [MADDER]))
    with pytest.raises(ExternalFailure):
        await faithful_check(found, facts(), ())
