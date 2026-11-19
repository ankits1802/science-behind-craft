from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import ComponentProposal, TaskReservation, User
from app.research.component_proposals import WAYS_ON, ComponentProposalDraft
from app.research.open_work import Viewer, WorkFilters
from app.services.component_proposals import propose_component
from app.services.open_work import list_open_work
from app.services.task_reservations import claim_task

from .open_work_seed import NOW, PROFESSOR, RESEARCHER, SITE, SLUG, WHAT_IF, opened_session

pytestmark = pytest.mark.db

MOLECULES_TASK = f"MISSING_COMPONENT:craft:{SLUG}:molecules"
CRYSTAL = "shared/chemistry/zircovane-crystal-lattice"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in opened_session():
        yield opened


def draft(**changes: Any) -> ComponentProposalDraft:
    values: dict[str, Any] = {
        "label": CRYSTAL,
        "title": "Zircovane crystal lattice",
        "description": "A turnable 3D model of the zircovane lattice, showing where the dye molecule docks.",
        "kind": "molecule_3d",
        "field": "CHEMISTRY",
        "subjects": [{"kind": "CRAFT", "key": SLUG}],
        "considered_labels": [WHAT_IF],
    }
    return ComponentProposalDraft.model_validate({**values, **changes})


async def person(session: AsyncSession, user_id: Any) -> User:
    found = await session.get(User, user_id)
    assert found is not None
    return found


async def test_a_close_match_in_the_library_refuses_the_proposal_with_the_ways_on(
    session: AsyncSession,
) -> None:
    copy = draft(
        label="open-work-test-craft/history/zircovane-skipped",
        title="What if the zircovane mordant is skipped",
        description="Shows the cloth with and without its zircovane mordant bath, side by side for the reader.",
        kind="what_if",
        field="HISTORY",
    )
    refused = await propose_component(session, await person(session, RESEARCHER), copy, now=NOW)
    assert refused.outcome == "REFUSED" and refused.proposal_id is None
    assert [match.component.label for match in refused.matches] == [WHAT_IF]
    assert "the same kind with a title sharing" in refused.matches[0].reasons[0]
    assert refused.ways_on == list(WAYS_ON)
    stored = await session.scalars(select(ComponentProposal.id).where(ComponentProposal.label == copy.label))
    assert stored.all() == []


async def test_a_new_component_waits_for_review_and_closes_the_task_it_completes(
    session: AsyncSession,
) -> None:
    await claim_task(session, RESEARCHER, MOLECULES_TASK, site=SITE, now=NOW)
    stored = await propose_component(
        session, await person(session, RESEARCHER), draft(task_key=MOLECULES_TASK), now=NOW
    )
    assert (stored.outcome, stored.status, stored.matches) == ("STORED", "PENDING", [])
    row = await session.get(ComponentProposal, stored.proposal_id)
    assert row is not None and (row.proposerId, row.reviewedById, row.consideredLabels) == (
        RESEARCHER,
        None,
        [WHAT_IF],
    )
    held = await session.scalar(select(TaskReservation).where(TaskReservation.taskKey == MOLECULES_TASK))
    assert held is not None and held.ending == "COMPLETED"
    work = await list_open_work(session, WorkFilters(craft_slug=SLUG), Viewer(), site=SITE, now=NOW)
    assert MOLECULES_TASK not in [task.key for task in work.tasks]
    with pytest.raises(InvalidInput, match="already waits"):
        await propose_component(session, await person(session, RESEARCHER), draft(), now=NOW)


async def test_a_professor_s_proposal_is_approved_at_once(session: AsyncSession) -> None:
    stored = await propose_component(session, await person(session, PROFESSOR), draft(), now=NOW)
    row = await session.get(ComponentProposal, stored.proposal_id)
    assert row is not None and (row.status, row.reviewedById, row.reviewedAt) == ("APPROVED", PROFESSOR, NOW)


async def test_a_subject_link_extends_the_component_it_names(session: AsyncSession) -> None:
    link = draft(label=WHAT_IF, kind="what_if", field="HISTORY", extends=WHAT_IF, extension="SUBJECT_LINK")
    stored = await propose_component(session, await person(session, RESEARCHER), link, now=NOW)
    assert (stored.outcome, stored.label) == ("STORED", WHAT_IF)


@pytest.mark.parametrize(
    ("changes", "says"),
    [
        ({"considered_labels": ["shared/chemistry/no-such-component"]}, "not in the component library"),
        ({"subjects": [{"kind": "CRAFT", "key": "No-Such-Craft-Anywhere"}]}, "No craft has the slug"),
        ({"subjects": [{"kind": "COMPOUND", "key": "not-an-id"}]}, "named by its id"),
        ({"subjects": [{"kind": "PLACE", "key": "Kachchh"}]}, "not a place key"),
    ],
)
async def test_a_proposal_names_real_labels_and_subjects(
    session: AsyncSession, changes: dict[str, Any], says: str
) -> None:
    with pytest.raises(InvalidInput, match=says):
        await propose_component(session, await person(session, RESEARCHER), draft(**changes), now=NOW)
