import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_session
from app.core.deps import get_current_user
from app.main import create_app
from app.models import User
from app.research.blocks import ReuseMarker
from app.research.explainer import Explainer
from app.services.piece_store import piece_id
from app.services.simulation_hiding import hidden_marked, simulation_piece_id

from ..contracts.explainer_golden import DOCUMENT, golden_json
from ..contracts.phase_c_golden import phase_c
from .fixtures import STORED_AT, golden_block, golden_simulation, water_citation

ANSWER = uuid.UUID("3b9f1e2d-6c7a-4d8b-9e0f-1a2b3c4d5e6f")
PATH = f"/api/answers/{ANSWER}/simulations/s1.b1/hidden"


@dataclass
class EmptySession:
    queries: list[Any] = field(default_factory=list)

    async def scalar(self, statement: Any) -> None:
        self.queries.append(statement)

    async def execute(self, statement: Any) -> None:
        self.queries.append(statement)


def client(role: str) -> tuple[TestClient, EmptySession]:
    session = EmptySession()
    user = User(id=uuid.UUID(int=11), name="Meera Rao", email="meera@example.org", role=role)

    async def one_session() -> AsyncIterator[EmptySession]:
        yield session

    async def signed_in() -> User:
        return user

    app = create_app()
    app.dependency_overrides[get_session] = one_session
    app.dependency_overrides[get_current_user] = signed_in
    return TestClient(app), session


@pytest.mark.parametrize("role", ["STUDENT", "RESEARCHER"])
def test_hiding_a_generated_explainer_is_refused_below_professor(role: str) -> None:
    http, session = client(role)
    for hidden in (True, False):
        response = http.put(PATH, json={"hidden": hidden})
        assert response.status_code == 403
    assert session.queries == []


@pytest.mark.parametrize("role", ["PROFESSOR", "ADMIN", "MASTER_ADMIN"])
def test_a_professor_and_above_reach_the_answer_and_find_nothing_kept(role: str) -> None:
    http, session = client(role)
    response = http.put(PATH, json={"hidden": True})
    assert response.status_code == 404
    assert len(session.queries) == 1


def test_the_hide_route_reads_one_boolean_and_one_block_id() -> None:
    http, _ = client("PROFESSOR")
    assert http.put(PATH, json={"hidden": "yes please"}).status_code == 422
    assert http.put(PATH, json={}).status_code == 422
    assert http.put(PATH.replace("s1.b1", "S1 B1"), json={"hidden": True}).status_code == 422


def test_a_block_is_hidden_through_the_piece_it_was_stored_as_or_reused_from() -> None:
    block = golden_block()
    assert simulation_piece_id(ANSWER, block) == piece_id(ANSWER, "s1.b1")
    marker = ReuseMarker(piece_id=uuid.uuid4(), stored_at=STORED_AT)
    assert simulation_piece_id(ANSWER, block.model_copy(update={"reuse": marker})) == marker.piece_id


def simulation_explainer() -> Explainer:
    source = next(s for s in phase_c()["sources"] if s["id"] == water_citation()["sourceId"])
    section = {
        "id": "s1",
        "discipline": "GEOGRAPHY",
        "title": "Geography and water",
        "order": 1,
        "state": "READY",
        "blocks": [golden_simulation()],
        "searched": None,
    }
    document = golden_json(DOCUMENT) | {"answerId": str(ANSWER), "sections": [section], "sources": [source]}
    return Explainer.model_validate(document)


def test_a_phase_a_explainer_has_no_simulation_to_mark() -> None:
    explainer = Explainer.model_validate(golden_json(DOCUMENT))
    assert hidden_marked(explainer, {"s1.b1", "s2.b1"}) == explainer


def test_a_read_back_explainer_marks_only_the_named_simulation_hidden() -> None:
    explainer = simulation_explainer()
    marked = hidden_marked(explainer, {"s1.b1"})
    (block,) = marked.sections[0].blocks
    assert block.hidden is True
    assert block.model_copy(update={"hidden": False}) == explainer.sections[0].blocks[0]
    assert hidden_marked(explainer, {"s1.b2"}) == explainer
