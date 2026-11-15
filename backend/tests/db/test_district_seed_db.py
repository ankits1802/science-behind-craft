import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.services.district_seed import seed_districts

pytestmark = pytest.mark.db


async def test_seed_districts_is_idempotent_and_builds_shapes() -> None:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            first = await seed_districts(session)
            assert first["states"] == 36
            assert first["districts"] == 786
            assert first["districtsWithShape"] == 752
            second = await seed_districts(session)
            assert second == first
            row = (
                await session.execute(
                    text(
                        "SELECT ST_GeometryType(geom), ST_IsValid(geom), ST_Contains(geom, centroid), name "
                        'FROM "AdminDistrict" WHERE lgd = 599'
                    )
                )
            ).one()
            assert row[0] == "ST_MultiPolygon"
            assert row[1] is True
            assert row[3]
            states_with_shape = (
                await session.execute(text('SELECT count(*) FROM "AdminState" WHERE geom IS NOT NULL'))
            ).scalar_one()
            assert states_with_shape >= 30
        finally:
            await transaction.rollback()
