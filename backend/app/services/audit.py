import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import current_request_id
from app.models import AuditLog

logger = logging.getLogger("kalavigyan.audit")


async def record(
    session: AsyncSession,
    *,
    action: str,
    actor: Any = None,
    target_type: str | None = None,
    target_id: Any = None,
    detail: dict[str, Any] | None = None,
    ip_hash: str | None = None,
) -> None:
    actor_id = getattr(actor, "id", None)
    session.add(
        AuditLog(
            actorId=actor_id,
            actorKind="USER" if actor_id else "SYSTEM",
            action=action,
            targetType=target_type,
            targetId=str(target_id) if target_id is not None else None,
            detail=detail,
            ipHash=ip_hash,
            requestId=current_request_id(),
        )
    )
    logger.info(
        "audit",
        extra={
            "action": action,
            "actorId": str(actor_id) if actor_id else None,
            "targetType": target_type,
            "targetId": str(target_id) if target_id is not None else None,
        },
    )
