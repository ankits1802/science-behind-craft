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
from app.research.blocks_play import hidden_block
from app.research.explainer import Explainer
from app.research.knowledge_pieces import piece_content_hash
from app.research.quiz import ExplainerQuiz, explainer_quiz
from app.services import knowledge_view
from app.services.explainer_payload import EXPLAINER_PAYLOAD_KEY, first_version_mark, version_document
from app.services.export_files import explainer_cited
from app.services.piece_store import piece_id

from ..contracts.explainer_golden import DOCUMENT, golden_json
from ..contracts.phase_c_golden import phase_c
from ..simulations.fixtures import golden_block, golden_simulation, water_citation

READER = User(id=uuid.UUID(int=7), name="Meera Rao", email="meera@example.org", role="STUDENT")
DOCUMENT_SOURCES = [source["id"] for source in golden_json(DOCUMENT)["sources"]]
WATER_SOURCE = water_citation()["sourceId"]
SIMULATION_ID = "s3.b9"


def with_simulation(*, hidden: bool) -> Explainer:
    document = golden_json(DOCUMENT)
    document["sections"][-1]["blocks"].append(golden_simulation() | {"id": SIMULATION_ID, "hidden": hidden})
    water = next(source for source in phase_c()["sources"] if source["id"] == WATER_SOURCE)
    document["sources"].append(water)
    return Explainer.model_validate(document)


def version_of(explainer: Explainer) -> Any:
    mark = first_version_mark(
        answer_id=explainer.answer_id, question=explainer.question, created_at=explainer.created_at
    )
    return version_document(mark, explainer)


def simulation() -> Any:
    return golden_block(id=SIMULATION_ID)


@dataclass
class Rows:
    rows: Sequence[tuple[Any, ...]]

    def first(self) -> tuple[Any, ...] | None:
        return self.rows[0] if self.rows else None

    def all(self) -> list[tuple[Any, ...]]:
        return list(self.rows)

    def tuples(self) -> Rows:
        return self


@dataclass
class HiddenPieceSession:
    hidden: Sequence[tuple[Any, ...]]
    asked: list[str] = field(default_factory=list)

    async def execute(self, statement: Any) -> Rows:
        sql = str(statement.compile(dialect=postgresql.dialect()))
        self.asked.append(sql)
        if '"KnowledgePiece"' in sql:
            return Rows(self.hidden)
        if '"Source"' in sql or '"EnvDataset"' in sql:
            return Rows(())
        explainer = with_simulation(hidden=False)
        return Rows(
            [(explainer.answer_id, {EXPLAINER_PAYLOAD_KEY: explainer.model_dump(mode="json", by_alias=True)})]
        )

    async def scalar(self, statement: Any) -> Any:
        self.asked.append(str(statement.compile(dialect=postgresql.dialect())))
        return {EXPLAINER_PAYLOAD_KEY: with_simulation(hidden=False).model_dump(mode="json", by_alias=True)}

    async def commit(self) -> None:
        return None


def client(session: HiddenPieceSession) -> TestClient:
    app = create_app()

    async def one_session() -> AsyncIterator[HiddenPieceSession]:
        yield session

    app.dependency_overrides[get_session] = one_session
    app.dependency_overrides[get_current_user] = lambda: READER
    return TestClient(app)


def hidden_piece() -> list[tuple[Any, ...]]:
    explainer = with_simulation(hidden=False)
    return [(piece_id(explainer.answer_id, SIMULATION_ID), piece_content_hash(simulation()))]


def test_only_a_hidden_generated_explainer_is_a_hidden_block() -> None:
    assert hidden_block(simulation().model_copy(update={"hidden": True}))
    assert not hidden_block(simulation())
    assert not any(
        hidden_block(block) for section in with_simulation(hidden=False).sections for block in section.blocks
    )


def test_a_hidden_generated_explainer_s_sources_leave_the_exports() -> None:
    shown = [thing.id for thing in explainer_cited(version_of(with_simulation(hidden=False)))]
    hidden = [thing.id for thing in explainer_cited(version_of(with_simulation(hidden=True)))]
    assert shown == [*DOCUMENT_SOURCES, WATER_SOURCE]
    assert hidden == DOCUMENT_SOURCES


@pytest.mark.parametrize(("pieces", "listed"), [([], True), (hidden_piece(), False)])
def test_the_citations_route_reads_the_hide_from_the_piece(
    pieces: list[tuple[Any, ...]], listed: bool
) -> None:
    explainer = with_simulation(hidden=False)
    session = HiddenPieceSession(pieces)
    reply = client(session).get(f"/api/explainers/{explainer.answer_id}/versions/1/citations")
    assert reply.status_code == 200, reply.text
    cited = [entry["sourceId"] for entry in reply.json()["entries"]]
    assert (WATER_SOURCE in cited) is listed
    assert [sid for sid in cited if sid != WATER_SOURCE] == DOCUMENT_SOURCES
    assert any('"KnowledgePiece"."hiddenAt" IS NOT NULL' in sql for sql in session.asked)


def test_the_quiz_route_reads_the_explainer_with_its_hidden_marks(monkeypatch: pytest.MonkeyPatch) -> None:
    async def every_claim_shown(
        session: Any, claim_ids: Sequence[uuid.UUID]
    ) -> tuple[dict[uuid.UUID, None], dict[Any, Any]]:
        return dict.fromkeys(claim_ids), {}

    monkeypatch.setattr(knowledge_view, "claims_by_id", every_claim_shown)
    explainer = with_simulation(hidden=False)
    session = HiddenPieceSession(hidden_piece())
    reply = client(session).get(f"/api/answers/{explainer.answer_id}/quiz")
    assert reply.status_code == 200, reply.text
    plain = Explainer.model_validate(golden_json(DOCUMENT))
    every = frozenset(c.claim_id for s in plain.sections for b in s.blocks for c in b.citations())
    assert ExplainerQuiz.model_validate(reply.json()) == explainer_quiz(plain, visible_claim_ids=every)
    assert any('"KnowledgePiece"."hiddenAt" IS NOT NULL' in sql for sql in session.asked)
