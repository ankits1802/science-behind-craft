from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import HTTPException, status

from app.services.export_files import ExportTools, opened_export_tools
from app.services.object_store import media_bucket

__all__ = ["EXPORT_UNAVAILABLE_DETAIL", "export_tools"]

EXPORT_UNAVAILABLE_DETAIL = "This file can't be made right now. Try again later."


async def export_tools() -> AsyncIterator[ExportTools]:
    objects = media_bucket()
    if objects is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, EXPORT_UNAVAILABLE_DETAIL)
    async with opened_export_tools(objects) as tools:
        yield tools
