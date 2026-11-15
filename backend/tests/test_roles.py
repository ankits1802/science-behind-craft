import json
from pathlib import Path

import pytest

from app.core.roles import (
    CAPABILITY_MIN_ROLE,
    MASTER_ADMIN,
    PROFESSOR,
    RESEARCHER,
    ROLE_RANK,
    STUDENT,
    Capability,
    assignable_roles,
    can,
    daily_allowance,
    may_assign,
    may_manage_target,
    requires_two_factor,
    role_rank,
)

SHARED_ROLES = Path(__file__).resolve().parents[2] / "shared" / "roles.json"


def test_role_ranks_match_plan() -> None:
    assert ROLE_RANK == {MASTER_ADMIN: 60, PROFESSOR: 40, RESEARCHER: 30, STUDENT: 15}


def test_unknown_role_has_no_rank() -> None:
    assert role_rank("ADMIN") == 0
    assert role_rank({"role": "PROFESSOR"}) == 40
    assert not can("ADMIN", Capability.ASK_STANDARD)


@pytest.mark.skipif(not SHARED_ROLES.exists(), reason="shared/roles.json not present")
def test_shared_roles_file_agrees() -> None:
    data = json.loads(SHARED_ROLES.read_text(encoding="utf-8"))
    ranks = data.get("ranks", data)
    assert {k: int(v) for k, v in ranks.items() if k in ROLE_RANK} == ROLE_RANK


MATRIX = {
    Capability.ASK_STANDARD: (True, True, True, True),
    Capability.ASK_DEEP: (False, True, True, True),
    Capability.VOICE: (True, True, True, True),
    Capability.GENERATE_IMAGE: (True, True, True, True),
    Capability.GENERATE_VIDEO: (False, True, True, True),
    Capability.SAVE_EXPORT: (True, True, True, True),
    Capability.READ_RESEARCHER_QUOTES: (False, True, True, True),
    Capability.PROPOSE_KNOWLEDGE: (False, True, True, True),
    Capability.RUN_ENRICHMENT: (False, True, True, True),
    Capability.ACCEPT_ALIASES: (False, True, True, True),
    Capability.MARK_CLAIM_LEVEL: (False, False, True, True),
    Capability.RETRACT_CLAIM: (False, False, True, True),
    Capability.SHARE_MEDIA: (False, False, True, True),
    Capability.HANDLE_OBJECTIONS: (False, False, True, True),
    Capability.MANAGE_ACCESS: (False, False, True, True),
    Capability.LIST_USERS: (False, False, True, True),
    Capability.INVITE_PROFESSORS: (False, False, False, True),
    Capability.CHANGE_ROLES: (False, False, False, True),
    Capability.DISABLE_USERS: (False, False, False, True),
    Capability.MANAGE_KEYS: (False, False, False, True),
    Capability.MANAGE_ROUTING: (False, False, False, True),
    Capability.MANAGE_QUOTAS: (False, False, False, True),
    Capability.MANAGE_CEILINGS: (False, False, False, True),
    Capability.MANAGE_DATASETS: (False, False, False, True),
    Capability.VIEW_USAGE: (False, False, False, True),
    Capability.VIEW_EVALUATION: (False, False, True, True),
    Capability.VIEW_AUDIT_LOG: (False, False, False, True),
}


def test_matrix_covers_every_capability() -> None:
    assert set(MATRIX) == set(Capability) == set(CAPABILITY_MIN_ROLE)


@pytest.mark.parametrize("capability", list(MATRIX))
def test_capability_matrix(capability: Capability) -> None:
    expected = MATRIX[capability]
    actual = tuple(can(role, capability) for role in (STUDENT, RESEARCHER, PROFESSOR, MASTER_ADMIN))
    assert actual == expected


def test_assignable_roles() -> None:
    assert assignable_roles(MASTER_ADMIN) == [MASTER_ADMIN, PROFESSOR, RESEARCHER, STUDENT]
    assert assignable_roles(PROFESSOR) == [RESEARCHER, STUDENT]
    assert assignable_roles(RESEARCHER) == []
    assert assignable_roles(STUDENT) == []
    assert may_assign(PROFESSOR, STUDENT)
    assert not may_assign(PROFESSOR, PROFESSOR)
    assert not may_assign(RESEARCHER, None)
    assert may_assign(PROFESSOR, None)


def test_manage_target() -> None:
    assert may_manage_target(MASTER_ADMIN, MASTER_ADMIN)
    assert may_manage_target(PROFESSOR, RESEARCHER)
    assert not may_manage_target(PROFESSOR, PROFESSOR)
    assert not may_manage_target(RESEARCHER, PROFESSOR)


def test_two_factor_required_roles() -> None:
    assert requires_two_factor(PROFESSOR)
    assert requires_two_factor(MASTER_ADMIN)
    assert not requires_two_factor(RESEARCHER)
    assert not requires_two_factor(STUDENT)


def test_daily_allowances_follow_plan() -> None:
    assert daily_allowance(STUDENT, "VOICE_SECONDS") == 600
    assert daily_allowance(RESEARCHER, "VOICE_SECONDS") == 1800
    assert daily_allowance(STUDENT, "IMAGE") == 5
    assert daily_allowance(PROFESSOR, "IMAGE") == 50
    assert daily_allowance(STUDENT, "VIDEO") == 0
    assert daily_allowance(PROFESSOR, "VIDEO") == 10
    assert daily_allowance(MASTER_ADMIN, "VIDEO") is None
