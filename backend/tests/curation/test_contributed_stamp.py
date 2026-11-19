import uuid
from typing import Any

from sqlalchemy import Select
from sqlalchemy.dialects import postgresql

from app.models import Craft
from app.services.contributed_pictures import shown_contributions
from app.services.craft_page_stamp import stamp_terms

CRAFT = uuid.UUID("5c0e0000-0000-4000-8000-000000000007")
CONTRIBUTED_TERMS = ["contributedCount", "contributedAt", "contributedAssetsCount", "contributedAssetsAt"]


def compiled(statement: Select[Any]) -> str:
    return str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def test_the_stamp_counts_and_dates_the_approved_pictures_and_their_files() -> None:
    names = [column.name for column in stamp_terms(Craft(id=CRAFT, slug="x", name="X")).selected_columns]
    assert [name for name in names if name.startswith("contributed")] == CONTRIBUTED_TERMS


def test_only_the_craft_s_approved_shared_pictures_count() -> None:
    shown = compiled(shown_contributions(CRAFT))
    assert "\"ImageContribution\".status = 'APPROVED'" in shown
    assert "\"MediaAsset\".visibility = 'CRAFT_SHARED'" in shown
    assert f'"ImageContribution"."craftId" = \'{CRAFT}\'' in shown
    assert "'image/gif'" not in shown and "'image/png', 'image/jpeg', 'image/webp'" in shown
    assert "craftId" not in compiled(shown_contributions())
