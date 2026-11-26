import uuid
from typing import Any

import pytest

from app.models import PageProposal
from app.research.page_proposal_review import PageScope
from app.research.staged_review_words import PageTouches
from app.services.page_proposal_reviews import page_touches

SITE = "https://kalavigyan.example"
PROPOSAL = uuid.UUID("0e000000-0000-4000-8000-000000024301")
LABEL = "sanganeri-hand-block-printing/chemistry/two-mordants-one-bath"
PLACE_LABEL = "sanganeri-hand-block-printing/place/where-sanganer-prints"
NONE = {"added": 0, "changed": 0, "removed": 0}
LINK = f"{SITE}/admin/review?proposal={PROPOSAL}"


def part(kind: str, queue: str, number: int, title: str, **more: Any) -> dict[str, Any]:
    return {
        "part": kind,
        "kind": queue,
        "id": f"0e000000-0000-4000-8000-0000000243{number:02d}",
        "title": title,
    } | more


ROW = PageProposal(
    id=PROPOSAL,
    userId=uuid.uuid4(),
    subjectKind="craft",
    subjectSlug="Sanganeri-Hand-Block-Printing",
    origin="AGENT",
    parts=[
        part("fact", "FACTS", 11, "Alum fixes the red.", chapter="chem"),
        part("component", "COMPONENTS", 12, "Black and red from one dye bath", chapter="chem", label=LABEL),
        part("component", "COMPONENTS", 13, "Where Sanganer prints", chapter="place", label=PLACE_LABEL),
        part("layout", "LAYOUTS", 14, "The page's layout"),
    ],
    changes=[
        {
            "key": "chem",
            "title": "The chemistry",
            "sentences": NONE,
            "components": NONE,
            "pictures": NONE,
            "changes": [],
        }
    ],
)


class OneRow:
    async def get(self, model: Any, key: uuid.UUID, **_: Any) -> Any:
        return ROW if key == PROPOSAL else None


@pytest.mark.parametrize(
    ("scope", "touches"),
    [
        (
            PageScope(),
            PageTouches(
                ("The chemistry", "place"), ("Black and red from one dye bath", "Where Sanganer prints"), LINK
            ),
        ),
        (
            PageScope(scope="CHAPTER", chapter="chem"),
            PageTouches(("The chemistry",), ("Black and red from one dye bath",), LINK),
        ),
        (
            PageScope(scope="COMPONENT", label=PLACE_LABEL),
            PageTouches(("place",), ("Where Sanganer prints",), LINK),
        ),
        (PageScope(scope="CHAPTER", chapter="history"), PageTouches((), (), LINK)),
    ],
)
async def test_a_page_decision_touches_the_chapters_and_components_of_the_parts_in_its_scope(
    scope: PageScope, touches: PageTouches
) -> None:
    session: Any = OneRow()
    assert await page_touches(session, PROPOSAL, scope, site=SITE) == touches


async def test_a_proposal_that_is_gone_touches_nothing() -> None:
    session: Any = OneRow()
    assert await page_touches(session, uuid.uuid4(), PageScope(), site=SITE) is None
