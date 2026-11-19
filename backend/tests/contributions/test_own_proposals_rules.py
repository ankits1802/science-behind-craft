import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.enums import CLAIM_STATUSES
from app.models.open_work import PROPOSAL_STATUSES
from app.research.knowledge_writes import GateReport
from app.research.own_proposals import (
    COMPONENT_STATES,
    CONTRIBUTION_TERMS_VERSION,
    FACT_STATES,
    ComponentProposalBody,
    OwnProposal,
    TermsAcceptance,
    component_reasons,
    component_state,
    fact_reasons,
    fact_state,
    newest_first,
    withdraw_refusal,
)

TERMS_DRAFT = Path(__file__).resolve().parents[3] / "docs" / "legal" / "contribution-terms.md"
PASSED = [GateReport(gate="QUOTES", passed=True, reasons=["every quote was found"])]
REFUSED_AT_SOURCE = [
    GateReport(gate="QUOTES", passed=True, reasons=["every quote was found"]),
    GateReport(
        gate="SOURCE", passed=False, reasons=["the fact rests only on D sources", "no stronger source"]
    ),
]


def test_every_stored_status_has_a_contributor_state() -> None:
    assert set(FACT_STATES) == set(CLAIM_STATUSES)
    assert set(COMPONENT_STATES) == set(PROPOSAL_STATUSES)


@pytest.mark.parametrize(
    ("status", "state"),
    [
        ("DRAFT", "WAITING"),
        ("PROPOSED", "PUBLISHED"),
        ("IN_REVIEW", "PUBLISHED"),
        ("APPROVED", "PUBLISHED"),
        ("WITHDRAWN", "WITHDRAWN"),
        ("RETRACTED", "RETIRED"),
        ("SUPERSEDED", "RETIRED"),
    ],
)
def test_a_fact_s_state_follows_what_a_reader_sees(status: str, state: str) -> None:
    assert fact_state(status, PASSED) == state


def test_a_fact_refused_at_a_gate_says_that_gate_s_reasons() -> None:
    assert fact_state("REJECTED", REFUSED_AT_SOURCE) == "REFUSED"
    assert fact_reasons("REFUSED", REFUSED_AT_SOURCE, "a reviewer's note never applies") == [
        "the fact rests only on D sources",
        "no stronger source",
    ]


def test_a_fact_a_reviewer_rejected_says_the_reviewer_s_reason() -> None:
    assert fact_state("REJECTED", PASSED) == "REJECTED"
    assert fact_reasons("REJECTED", PASSED, "  The GI record says otherwise.  ") == [
        "The GI record says otherwise."
    ]
    assert fact_reasons("REJECTED", PASSED, "   ") == []
    assert fact_reasons("REJECTED", PASSED, None) == []
    assert fact_reasons("PUBLISHED", PASSED, "A note on a published fact is not a reason") == []


def test_a_component_proposal_s_state_and_its_reviewer_s_reason() -> None:
    assert [component_state(status) for status in ("PENDING", "APPROVED", "REJECTED", "WITHDRAWN")] == [
        "WAITING",
        "APPROVED",
        "REJECTED",
        "WITHDRAWN",
    ]
    assert component_reasons("REJECTED", "A map of Kachchh already shows this.") == [
        "A map of Kachchh already shows this."
    ]
    assert component_reasons("APPROVED", "Build it with the river layer.") == []


def test_an_unknown_status_fails_loudly() -> None:
    with pytest.raises(ValueError, match="'ARCHIVED' has no contributor state"):
        fact_state("ARCHIVED", [])
    with pytest.raises(ValueError, match="'BUILT'"):
        component_state("BUILT")


def test_only_what_still_waits_may_be_withdrawn_because_consent_cannot_be_revoked() -> None:
    assert withdraw_refusal("WAITING") is None
    assert "consent cannot be revoked" in (withdraw_refusal("PUBLISHED") or "")
    assert "approved contribution stays" in (withdraw_refusal("APPROVED") or "")
    for state in ("REFUSED", "REJECTED", "WITHDRAWN", "RETIRED"):
        assert withdraw_refusal(state) == "It no longer waits for review, so there is nothing to withdraw."


def _item(minute: int, name: str) -> OwnProposal:
    return OwnProposal(
        id=uuid.uuid5(uuid.NAMESPACE_URL, f"own-proposals/{name}"),
        kind="FACT",
        state="WAITING",
        status="DRAFT",
        text=name,
        field="PROCESS",
        subject_name="Kutch Ajrakh",
        craft_slug="Kutch-Ajrakh",
        created_at=datetime(2026, 11, 19, 10, minute, tzinfo=UTC),
    )


def test_facts_and_components_are_listed_newest_first_up_to_the_limit() -> None:
    items = [_item(5, "five"), _item(20, "twenty"), _item(1, "one"), _item(12, "twelve")]
    assert [item.text for item in newest_first(items)] == ["twenty", "twelve", "five", "one"]
    assert [item.text for item in newest_first(items, limit=2)] == ["twenty", "twelve"]


def test_the_terms_version_is_the_one_the_legal_draft_names() -> None:
    heading = TERMS_DRAFT.read_text(encoding="utf-8").splitlines()[0]
    named = re.search(r"version (\d{4}-\d{2}-\d{2})", heading)
    assert named is not None and named.group(1) == CONTRIBUTION_TERMS_VERSION == "2026-11-19"
    assert TermsAcceptance.model_validate({"version": "2026-11-19"}).version == "2026-11-19"
    with pytest.raises(ValidationError):
        TermsAcceptance.model_validate({"version": "2025-01-01"})


def test_the_site_s_component_proposal_is_camel_case_and_keeps_the_draft_s_rules() -> None:
    body = {
        "label": "kutch-ajrakh/chemistry/indigo-vat-redox",
        "title": "The indigo vat's reduction",
        "description": "Shows indigo reduced to pale yellow leucoindigo in the vat and blued again in the air.",
        "kind": "reaction_player",
        "field": "CHEMISTRY",
        "craftSlug": "Kutch-Ajrakh",
        "subjects": [{"kind": "CRAFT", "key": "Kutch-Ajrakh"}],
        "consideredLabels": ["kutch-ajrakh/chemistry/indigo-vat"],
        "taskKey": "MISSING_COMPONENT:craft:Kutch-Ajrakh:reaction-player",
    }
    draft = ComponentProposalBody.model_validate(body)
    assert (draft.craft_slug, draft.considered_labels, draft.task_key) == (
        "Kutch-Ajrakh",
        ["kutch-ajrakh/chemistry/indigo-vat"],
        "MISSING_COMPONENT:craft:Kutch-Ajrakh:reaction-player",
    )
    with pytest.raises(ValidationError, match="extends and extension come together"):
        ComponentProposalBody.model_validate({**body, "extends": "kutch-ajrakh/chemistry/indigo-vat"})
