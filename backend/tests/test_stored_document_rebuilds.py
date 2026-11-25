from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.errors import InvalidInput
from app.research.page_revalidation import PageOwners
from app.services import stored_document_rebuilds as rebuilds
from app.services.stored_documents import Rebuilt

REBUILT_AT = datetime(2026, 11, 25, 9, 0, tzinfo=UTC)
SENT_AT = REBUILT_AT + timedelta(seconds=2)


@dataclass
class Seen:
    outcome: Any = Rebuilt.CHANGED
    confirmed: bool = True
    rebuilt: list[str] = field(default_factory=list)
    refreshed: list[PageOwners] = field(default_factory=list)
    dropped: list[tuple[str, str, datetime]] = field(default_factory=list)

    async def rebuild(self, session: Any, subject: Any, *, now: Any) -> Rebuilt:
        self.rebuilt.append(f"{subject.kind}:{subject.slug}")
        return self.outcome

    async def refresh(self, owners: PageOwners) -> bool:
        self.refreshed.append(owners)
        return self.confirmed

    async def drop_withheld(self, session: Any, kind: str, slug: str, *, before: datetime) -> None:
        self.dropped.append((kind, slug, before))


def patched(
    monkeypatch: pytest.MonkeyPatch,
    *,
    here: bool = True,
    locked: bool = True,
    outcome: Any = Rebuilt.CHANGED,
    confirmed: bool = True,
) -> Seen:
    seen = Seen(outcome=outcome, confirmed=confirmed)
    clock = iter([REBUILT_AT, SENT_AT])

    @asynccontextmanager
    async def scope() -> AsyncIterator[object]:
        yield object()

    async def rebuilds_here(session: Any) -> bool:
        return here

    async def lock(session: Any) -> bool:
        return locked

    async def subject(session: Any, kind: str, slug: str) -> Any:
        if slug == "No-Such-Craft":
            raise InvalidInput("No craft has the slug No-Such-Craft.")
        return SimpleNamespace(kind=kind, slug=slug)

    monkeypatch.setattr(rebuilds, "session_scope", scope)
    monkeypatch.setattr(rebuilds, "rebuilds_here", rebuilds_here)
    monkeypatch.setattr(rebuilds, "_rebuild_lock", lock)
    monkeypatch.setattr(rebuilds, "subject_by_key", subject)
    monkeypatch.setattr(rebuilds, "rebuild_document", seen.rebuild)
    monkeypatch.setattr(rebuilds, "refresh_pages", seen.refresh)
    monkeypatch.setattr(rebuilds, "drop_withheld", seen.drop_withheld)
    monkeypatch.setattr(rebuilds, "utc_now", lambda: next(clock))
    return seen


async def test_a_queued_rebuild_that_changes_a_craft_refreshes_its_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = patched(monkeypatch)
    await rebuilds.rebuild_wanted("craft", "Bagh-Print")
    assert seen.rebuilt == ["craft:Bagh-Print"]
    assert seen.refreshed == [PageOwners(crafts=("Bagh-Print",))]


async def test_a_category_rebuild_refreshes_the_category_and_an_unchanged_one_refreshes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = patched(monkeypatch, outcome=Rebuilt.REMOVED)
    await rebuilds.rebuild_wanted("category", "Metal-Craft-Category")
    assert seen.refreshed == [PageOwners(categories=("Metal-Craft-Category",))]
    quiet = patched(monkeypatch, outcome=Rebuilt.UNCHANGED)
    await rebuilds.rebuild_wanted("family", "Applique")
    assert (quiet.rebuilt, quiet.refreshed) == (["family:Applique"], [])


@pytest.mark.parametrize(("here", "locked"), [(False, True), (True, False)], ids=["older release", "busy"])
async def test_another_release_or_a_running_rebuild_leaves_the_read_s_request_for_later(
    monkeypatch: pytest.MonkeyPatch, here: bool, locked: bool
) -> None:
    seen = patched(monkeypatch, here=here, locked=locked)
    await rebuilds.rebuild_wanted("craft", "Bagh-Print")
    assert (seen.rebuilt, seen.refreshed) == ([], [])


async def test_a_subject_gone_since_the_read_is_logged_and_nothing_is_refreshed(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    seen = patched(monkeypatch)
    await rebuilds.rebuild_wanted("craft", "No-Such-Craft")
    assert (seen.rebuilt, seen.refreshed) == ([], [])
    assert "could not be rebuilt after a read" in caplog.text


async def test_a_confirmed_refresh_after_a_rebuild_drops_the_page_s_withheld_versions_replaced_before_it_was_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = patched(monkeypatch)
    await rebuilds.rebuild_wanted("craft", "Sanganeri-Hand-Block-Printing")
    assert seen.refreshed == [PageOwners(crafts=("Sanganeri-Hand-Block-Printing",))]
    assert seen.dropped == [("craft", "Sanganeri-Hand-Block-Printing", SENT_AT)]


async def test_a_refresh_the_web_did_not_confirm_drops_nothing_and_leaves_the_version_to_its_grace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = patched(monkeypatch, confirmed=False)
    await rebuilds.rebuild_wanted("family", "Applique")
    assert (seen.rebuilt, seen.refreshed) == (["family:Applique"], [PageOwners(crafts=("Applique",))])
    assert seen.dropped == []
    quiet = patched(monkeypatch, outcome=Rebuilt.UNCHANGED)
    await rebuilds.rebuild_wanted("category", "Metal-Craft-Category")
    assert (quiet.refreshed, quiet.dropped) == ([], [])


def test_a_rebuilt_document_moved_only_when_it_was_built_changed_or_removed() -> None:
    assert [outcome.value for outcome in Rebuilt if outcome.moved] == ["built", "changed", "removed"]
