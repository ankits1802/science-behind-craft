import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.core.db import get_session
from app.core.deps import get_current_user
from app.main import create_app
from app.models import User
from app.research.knowledge_pieces import piece_content_hash
from app.services.answer_store import EXPLAINER_PAYLOAD_KEY
from app.services.piece_store import piece_id

from .fixtures import golden_block
from .test_simulation_hiding import ANSWER, simulation_explainer

READER = uuid.UUID(int=11)


@dataclass
class Rows:
    rows: Sequence[tuple[Any, ...]]

    def first(self) -> tuple[Any, ...] | None:
        return self.rows[0] if self.rows else None

    def all(self) -> list[tuple[Any, ...]]:
        return list(self.rows)


@dataclass
class ScriptedSession:
    hidden: Sequence[tuple[Any, ...]]
    asked: list[str] = field(default_factory=list)

    async def execute(self, statement: Any) -> Rows:
        sql = str(statement.compile(dialect=postgresql.dialect()))
        self.asked.append(sql)
        if sql.startswith("UPDATE"):
            return Rows(())
        if '"KnowledgePiece"' in sql:
            return Rows(self.hidden)
        payload = {EXPLAINER_PAYLOAD_KEY: simulation_explainer().model_dump(mode="json", by_alias=True)}
        latest = sql.startswith('SELECT "Answer".id, "Answer"."explainerVersion"')
        return Rows([(ANSWER, 1, payload)] if latest else [(ANSWER, payload)])

    async def commit(self) -> None:
        return None


def read_back(path: str, hidden: Sequence[tuple[Any, ...]]) -> tuple[dict[str, Any], ScriptedSession]:
    session = ScriptedSession(hidden)
    user = User(id=READER, name="Meera Rao", email="meera@example.org", role="STUDENT")

    async def one_session() -> AsyncIterator[ScriptedSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_session] = one_session
    app.dependency_overrides[get_current_user] = lambda: user
    response = TestClient(app).get(path)
    assert response.status_code == 200, response.text
    return response.json(), session


def simulation_of(document: dict[str, Any]) -> dict[str, Any]:
    (block,) = document["explainer"]["sections"][0]["blocks"]
    return block


@pytest.mark.parametrize("path", [f"/api/explainers/{ANSWER}", f"/api/explainers/{ANSWER}/versions/1"])
def test_a_stored_explainer_read_back_marks_the_simulation_its_hidden_piece_hides(path: str) -> None:
    block = golden_block()
    document, session = read_back(path, [(piece_id(ANSWER, block.id), piece_content_hash(block))])
    assert simulation_of(document)["hidden"] is True
    (asked,) = [sql for sql in session.asked if '"KnowledgePiece"' in sql]
    assert '"KnowledgePiece"."hiddenAt" IS NOT NULL' in asked
    assert '"KnowledgePiece"."contentHash" IN' in asked


def test_a_simulation_whose_piece_is_shown_reads_back_as_stored() -> None:
    document, _ = read_back(f"/api/explainers/{ANSWER}", [])
    assert simulation_of(document)["hidden"] is False
    assert simulation_of(document) == golden_block().model_dump(mode="json", by_alias=True)


def test_a_block_carried_into_a_later_version_is_hidden_through_the_piece_an_earlier_answer_kept() -> None:
    earlier = piece_id(uuid.uuid4(), golden_block().id)
    document, _ = read_back(f"/api/explainers/{ANSWER}", [(earlier, piece_content_hash(golden_block()))])
    assert simulation_of(document)["hidden"] is True
