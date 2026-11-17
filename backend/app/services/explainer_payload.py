from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.research.explainer import Explainer
from app.research.explainer_versions import (
    EXPLAINER_VERSION_SCHEMA_VERSION,
    ExplainerVersionDocument,
    VersionMark,
)

__all__ = [
    "EXPLAINER_PAYLOAD_KEY",
    "FIRST_VERSION",
    "VERSION_PAYLOAD_KEY",
    "first_version_mark",
    "stored_explainer",
    "stored_mark",
    "stored_payload",
    "stored_version",
    "version_document",
]

logger = logging.getLogger(__name__)

EXPLAINER_PAYLOAD_KEY = "explainer"
VERSION_PAYLOAD_KEY = "version"
FIRST_VERSION = 1


def first_version_mark(*, answer_id: uuid.UUID, question: str, created_at: datetime | str) -> VersionMark:
    return VersionMark.model_validate(
        {
            "explainerId": answer_id,
            "version": FIRST_VERSION,
            "answerId": answer_id,
            "basedOn": None,
            "question": question,
            "changes": [],
            "createdAt": created_at,
        }
    )


def version_document(mark: VersionMark, explainer: Explainer) -> ExplainerVersionDocument:
    return ExplainerVersionDocument(
        schema_version=EXPLAINER_VERSION_SCHEMA_VERSION, mark=mark, explainer=explainer
    )


def stored_payload(explainer: Explainer, mark: VersionMark | None) -> dict[str, Any]:
    payload = {EXPLAINER_PAYLOAD_KEY: explainer.model_dump(mode="json", by_alias=True)}
    if mark is not None:
        payload[VERSION_PAYLOAD_KEY] = mark.model_dump(mode="json", by_alias=True)
    return payload


def stored_explainer(answer_id: uuid.UUID, payload: dict[str, Any] | None) -> Explainer | None:
    document = payload.get(EXPLAINER_PAYLOAD_KEY) if isinstance(payload, dict) else None
    if document is None:
        return None
    try:
        explainer = Explainer.model_validate(document)
    except ValidationError as error:
        logger.error("answer %s keeps an explainer that is off its contract: %s", answer_id, error)
        return None
    if explainer.answer_id != answer_id:
        logger.error("answer %s keeps the explainer of answer %s", answer_id, explainer.answer_id)
        return None
    return explainer


def stored_version(
    answer_id: uuid.UUID, number: int, payload: dict[str, Any] | None
) -> ExplainerVersionDocument:
    explainer = stored_explainer(answer_id, payload)
    if explainer is None:
        raise InvalidInput(f"answer {answer_id} is version {number} of an explainer but keeps none")
    if number == FIRST_VERSION:
        mark = first_version_mark(
            answer_id=answer_id, question=explainer.question, created_at=explainer.created_at
        )
    else:
        mark = stored_mark(answer_id, number, (payload or {}).get(VERSION_PAYLOAD_KEY))
    return version_document(mark, explainer)


def stored_mark(answer_id: uuid.UUID, number: int, stored: Any) -> VersionMark:
    try:
        mark = VersionMark.model_validate(stored)
    except ValidationError as error:
        raise InvalidInput(f"answer {answer_id} keeps a version mark that is off its contract") from error
    if (mark.answer_id, mark.version) != (answer_id, number):
        raise InvalidInput(f"answer {answer_id} is version {number} but keeps the mark of another version")
    return mark
