import uuid
from typing import Any

from sqlalchemy.dialects import postgresql

from app.models import Craft
from app.services.craft_process import _load_rows


class Empty:
    def all(self) -> list[Any]:
        return []


class RecordingSession:
    def __init__(self) -> None:
        self.statements: list[str] = []

    async def scalars(self, statement: Any) -> Empty:
        self.statements.append(_sql(statement))
        return Empty()

    async def execute(self, statement: Any) -> Empty:
        self.statements.append(_sql(statement))
        return Empty()


def _sql(statement: Any) -> str:
    return " ".join(str(statement.compile(dialect=postgresql.dialect())).split())


async def test_every_process_query_reads_in_a_total_order_so_a_page_rebuilds_the_same() -> None:
    session = RecordingSession()
    rows = await _load_rows(session, Craft(id=uuid.UUID(int=7), slug="Test-Craft", name="Test Craft"))  # type: ignore[arg-type]
    assert rows.processes == rows.stages == rows.materials == rows.reactions == []
    orders = [sql[sql.index(" ORDER BY ") :] for sql in session.statements]
    assert orders == [
        ' ORDER BY "Process".name, "Process".variant, "Process".id',
        ' ORDER BY "ProcessStage"."processId", "ProcessStage".ordinal, "ProcessStage".id',
        ' ORDER BY "Reaction"."stageId", "Reaction".ordinal, "Reaction".id',
        ' ORDER BY "ProcessCondition".id',
        ' ORDER BY "StageMaterial"."stageId", "Material".name, "StageMaterial".id',
        ' ORDER BY "ReactionCitation"."reactionId", "ClaimSource".id',
        ' ORDER BY "ConditionReading"."conditionId", "ConditionReading".id',
    ]
