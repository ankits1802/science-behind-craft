import pytest

from app.core.errors import InvalidInput
from app.research.review_switch import (
    ReviewSwitch,
    ReviewSwitchUpdate,
    placement,
    refused_placement,
    stored_switch,
)
from app.services import app_settings


def test_the_owner_s_defaults_are_auto_for_research_and_approval_for_contributors_and_agents() -> None:
    switch = ReviewSwitch()
    assert switch.stored() == {"RESEARCH": "AUTO", "CONTRIBUTION": "APPROVAL", "AGENT": "APPROVAL"}
    assert app_settings.DEFAULTS[app_settings.REVIEW_SWITCH] == switch.stored()
    assert stored_switch(None) == switch


def test_auto_publishes_unreviewed_and_keeps_the_fact_in_the_queue() -> None:
    placed = placement("AUTO", proposer_reviews=False)
    assert (placed.outcome, placed.status, placed.approved_at_once, placed.queued) == (
        "PUBLISHED",
        "IN_REVIEW",
        False,
        True,
    )
    assert placed.live


def test_approval_holds_the_fact_hidden_until_a_reviewer_approves() -> None:
    placed = placement("APPROVAL", proposer_reviews=False)
    assert (placed.outcome, placed.status, placed.queued, placed.live) == ("WAITING", "DRAFT", True, False)


@pytest.mark.parametrize("mode", ["AUTO", "APPROVAL"])
def test_a_reviewer_s_own_fact_is_approved_at_once_whatever_the_switch(mode: str) -> None:
    placed = placement(mode, proposer_reviews=True)
    assert (placed.outcome, placed.status, placed.approved_at_once, placed.queued) == (
        "PUBLISHED",
        "APPROVED",
        True,
        False,
    )


def test_a_refused_fact_is_rejected_and_never_queued() -> None:
    placed = refused_placement()
    assert (placed.outcome, placed.status, placed.queued, placed.live) == (
        "REFUSED",
        "REJECTED",
        False,
        False,
    )


def test_an_update_changes_only_the_origins_it_names() -> None:
    changed = ReviewSwitchUpdate(agent="AUTO").applied_to(ReviewSwitch())
    assert changed.stored() == {"RESEARCH": "AUTO", "CONTRIBUTION": "APPROVAL", "AGENT": "AUTO"}
    assert changed.mode("AGENT") == "AUTO"


def test_a_stored_switch_is_read_back_and_a_malformed_one_fails_loudly() -> None:
    assert stored_switch({"RESEARCH": "APPROVAL"}).stored()["RESEARCH"] == "APPROVAL"
    with pytest.raises(InvalidInput):
        stored_switch({"READERS": "AUTO"})
    with pytest.raises(InvalidInput):
        stored_switch({"AGENT": "SOMETIMES"})
    with pytest.raises(InvalidInput):
        ReviewSwitch().mode("READERS")
    with pytest.raises(InvalidInput):
        placement("SOMETIMES", proposer_reviews=False)
