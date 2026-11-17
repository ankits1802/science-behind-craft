import uuid
from typing import Any

import pytest

from app.api.routes import knowledge
from app.research.explainer_versions import BuildsOn
from app.services.explainer_history import StaleVersion, UnknownExplainer
from app.services.follow_ups import FollowUp

from .alerts.versions import base_version
from .test_knowledge import Asked, signed_in

EXPLAINER = "0c5e7a1d-2b3f-4c6d-8e9f-a0b1c2d3e4f5"
FOLLOW_UP = {
    "question": "Why did the printers move?",
    "buildsOn": {"explainerId": EXPLAINER, "version": 1, "facets": []},
}


def found_by(outcome: Any) -> Any:
    async def follow_up_of(session: Any, user_id: uuid.UUID, builds_on: BuildsOn) -> FollowUp:
        assert user_id == uuid.UUID(int=7)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return follow_up_of


@pytest.mark.parametrize(
    "extra", [{"craftSlug": "Bagru"}, {"anyCraft": True}, {"depth": "BASIC"}, {"language": "hi"}]
)
def test_a_follow_up_keeps_the_explainer_s_craft_depth_and_language(extra: dict[str, Any]) -> None:
    response = signed_in("STUDENT").post("/api/answers/stream", json=FOLLOW_UP | extra)
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("outcome", "status"),
    [(UnknownExplainer(uuid.UUID(EXPLAINER)), 404), (StaleVersion(uuid.UUID(EXPLAINER), 1, 2), 409)],
)
def test_a_follow_up_on_another_reader_s_or_an_older_version_is_refused(
    monkeypatch: pytest.MonkeyPatch, outcome: Exception, status: int
) -> None:
    monkeypatch.setattr(knowledge, "follow_up_of", found_by(outcome))
    response = signed_in("STUDENT").post("/api/answers/stream", json=FOLLOW_UP)
    assert response.status_code == status


def test_a_follow_up_runs_at_the_explainer_s_depth_in_its_language_for_its_craft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = base_version()
    monkeypatch.setattr(knowledge, "follow_up_of", found_by(FollowUp(base=base)))
    asked = Asked()
    response = signed_in("STUDENT", asked).post("/api/answers/stream", json=FOLLOW_UP)
    assert response.status_code == 200
    assert asked.depths == ["EXPERT"]
    (understood,) = asked.understood
    assert (understood.craft_slug, understood.language, understood.depth) == ("Kutch-Ajrakh", "en", "EXPERT")
    names = [
        line.removeprefix("event: ") for line in response.text.splitlines() if line.startswith("event: ")
    ]
    assert names == ["understood", "builds_on", "error", "done"]
