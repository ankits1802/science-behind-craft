import pytest

from app.core.errors import InvalidInput
from app.core.roles import ROLE_RANK, UNCAPPED_ROLES, is_uncapped
from app.research.depth import (
    DEPTH_POLICIES,
    ROLE_DEFAULT_DEPTHS,
    default_depth,
    depth_at_least,
    depth_policy,
    effective_depth,
    research_budget,
    selectable_depths,
)

PLAN_TABLE = {
    "BASIC": ("Basic", "HYBRID", (3, 4), (2, 2)),
    "DETAILED": ("Detailed", "HYBRID", (5, 7), (4, 4)),
    "EXPERT": ("Expert", "DEEP", (1, 14), (6, 12)),
}


@pytest.mark.parametrize("depth", sorted(PLAN_TABLE))
def test_each_depth_follows_the_plan_table(depth: str) -> None:
    policy = depth_policy(depth)
    label, mode, sections, experts = PLAN_TABLE[depth]
    assert (policy.label, policy.mode) == (label, mode)
    assert (policy.min_sections, policy.max_sections) == sections
    assert (policy.min_experts, policy.max_experts) == experts


def test_roles_default_to_their_plan_depth() -> None:
    assert dict(ROLE_DEFAULT_DEPTHS) == {
        "STUDENT": "BASIC",
        "ARTISAN": "BASIC",
        "RESEARCHER": "DETAILED",
        "PROFESSOR": "DETAILED",
        "ADMIN": "EXPERT",
        "MASTER_ADMIN": "EXPERT",
    }
    assert set(ROLE_DEFAULT_DEPTHS) == set(ROLE_RANK)
    assert default_depth({"role": "ADMIN"}) == "EXPERT"
    assert default_depth("VISITOR") == "BASIC"


def test_anyone_can_switch_depth_and_an_unknown_role_cannot() -> None:
    for role in ROLE_RANK:
        assert selectable_depths(role) == ("BASIC", "DETAILED", "EXPERT")
    assert selectable_depths("VISITOR") == ()
    assert selectable_depths(None) == ()


def test_master_admins_have_no_caps_and_nobody_else_is_uncapped() -> None:
    assert frozenset({"MASTER_ADMIN"}) == UNCAPPED_ROLES
    assert [role for role in ROLE_RANK if is_uncapped(role)] == ["MASTER_ADMIN"]
    assert effective_depth("EXPERT", "MASTER_ADMIN", past_degrade=True) == "EXPERT"


def test_past_the_degrade_mark_expert_becomes_detailed_for_capped_roles() -> None:
    assert effective_depth("EXPERT", "ADMIN", past_degrade=True) == "DETAILED"
    assert effective_depth("EXPERT", "STUDENT", past_degrade=True) == "DETAILED"
    assert effective_depth("EXPERT", "ADMIN", past_degrade=False) == "EXPERT"
    assert effective_depth("DETAILED", "STUDENT", past_degrade=True) == "DETAILED"
    assert effective_depth("BASIC", "STUDENT", past_degrade=True) == "BASIC"
    with pytest.raises(InvalidInput):
        effective_depth("DEEP", "ADMIN", past_degrade=False)


def test_depths_are_ordered_basic_detailed_expert() -> None:
    assert depth_at_least("EXPERT", "BASIC") and depth_at_least("DETAILED", "DETAILED")
    assert not depth_at_least("BASIC", "DETAILED")
    assert list(DEPTH_POLICIES) == ["BASIC", "DETAILED", "EXPERT"]


@pytest.mark.parametrize(
    ("depth", "mode", "queries", "fetches"),
    [("BASIC", "HYBRID", 2, 5), ("DETAILED", "HYBRID", 4, 10), ("EXPERT", "DEEP", 24, 48)],
)
def test_each_depth_researches_within_its_budget(depth: str, mode: str, queries: int, fetches: int) -> None:
    budget = research_budget(mode, depth)
    assert (budget.max_queries, budget.max_fetches) == (queries, fetches)


def test_a_degraded_expert_answer_keeps_the_hybrid_limits() -> None:
    budget = research_budget("HYBRID", "EXPERT")
    assert (budget.max_queries, budget.max_fetches) == (4, 10)
    assert research_budget("VERIFIED", "EXPERT").max_queries == 0


def test_without_a_depth_the_mode_sets_the_budget() -> None:
    assert research_budget("DEEP").max_fetches == 48


def test_a_depth_may_not_research_beyond_its_mode() -> None:
    fields = DEPTH_POLICIES["BASIC"].model_dump() | {"maxQueries": 5}
    with pytest.raises(ValueError, match="within the limits of HYBRID"):
        type(DEPTH_POLICIES["BASIC"]).model_validate(fields)
