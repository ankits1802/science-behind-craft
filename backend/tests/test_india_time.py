from datetime import UTC, datetime, timedelta

from app.core.clock import INDIA_TZ, INDIA_TZ_NAME
from app.providers.budget import day_start, month_start
from app.services.naming import PlaceParts, file_name

LATE_EVENING_UTC = datetime(2026, 11, 30, 18, 45, tzinfo=UTC)
NEXT_INDIA_DAY = datetime(2026, 11, 30, 18, 30, tzinfo=UTC)


def test_india_is_five_and_a_half_hours_ahead_all_year() -> None:
    assert INDIA_TZ_NAME == "Asia/Kolkata"
    for month in (1, 7):
        offset = datetime(2026, month, 15, 12, tzinfo=UTC).astimezone(INDIA_TZ).utcoffset()
        assert offset == timedelta(hours=5, minutes=30)


def test_quota_days_and_file_names_turn_over_at_the_same_midnight() -> None:
    assert day_start(LATE_EVENING_UTC) == NEXT_INDIA_DAY
    assert month_start(LATE_EVENING_UTC) == NEXT_INDIA_DAY
    name = file_name(
        entity="Generated-Image",
        what="Image",
        ext="png",
        moment=LATE_EVENING_UTC,
        place=PlaceParts(locality=None, district=None, state=None),
        craft=None,
        subject=None,
        sequence=None,
    )
    assert name.startswith("KalaVigyan_Generated-Image_2026-12-01_0015")
