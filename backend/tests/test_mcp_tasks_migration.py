from app.models import McpTask
from app.models.oauth import MCP_TASK_STATUSES
from app.services.mcp_task_store import CANCELLED, COMPLETED, FAILED, WORKING

from .migration_scripts import migration

STEP = migration("0123_mcp_tasks")


def test_the_task_table_follows_the_coded_figures_migration() -> None:
    assert (STEP.revision, STEP.down_revision) == ("0123_mcp_tasks", "0122_review_diff")


def test_the_migration_and_the_model_hold_the_same_statuses_and_bounds() -> None:
    assert McpTask.__tablename__ == STEP.TABLE
    assert STEP.STATUSES == MCP_TASK_STATUSES == (WORKING, COMPLETED, FAILED, CANCELLED)
    assert STEP.STATUSES == ("working", "completed", "failed", "cancelled")
    columns = McpTask.__table__.c
    assert columns["id"].type.length == STEP.TASK_ID_CHARS
    assert columns["statusMessage"].type.length == STEP.MESSAGE_CHARS
    assert STEP.DIGEST_CHARS == columns["argumentsHash"].type.length == 64
    assert {"userId", "tool", "argumentsHash", "status", "result", "error", "createdAt", "expiresAt"} <= set(
        columns.keys()
    )
