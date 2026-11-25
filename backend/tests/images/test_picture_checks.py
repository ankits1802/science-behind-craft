import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest

from app.core.errors import InvalidInput
from app.research.open_work import TASK_KINDS, UNRESERVABLE_KINDS, WorkFilters, parse_task_key
from app.research.picture_checks import (
    HIDDEN,
    IN_REVIEW,
    PICTURE_CHECK_TASK,
    SEEN,
    WAITING,
    StoredVerdict,
    check_key,
    checked_state,
    state_word,
)
from app.services.open_work_picture_checks import picture_check_tasks
from app.services.section_images import stored_items
from app.services.served_pictures import served_picture
from app.services.task_reservations import CHECKS_NOT_RESERVED, claim_task

from .fakes import AJRAKH_WORLD, candidate, stored_picture

MEERA, ARJUN, ADMIN = (uuid.UUID(int=n) for n in (1, 2, 3))
FACT, OTHER_FACT = uuid.UUID(int=10), uuid.UUID(int=11)


def look(user: uuid.UUID, *, shows: bool, trusted: bool = False) -> StoredVerdict:
    return StoredVerdict(user_id=user, shows=shows, trusted=trusted, ruling=False)


def ruling(*, shows: bool) -> StoredVerdict:
    return StoredVerdict(user_id=ADMIN, shows=shows, trusted=True, ruling=True)


def said(*verdicts: StoredVerdict) -> str:
    return state_word(checked_state(verdicts))


def test_a_shows_from_an_untrusted_account_waits_and_a_second_account_agreeing_marks_it_seen() -> None:
    assert said(look(MEERA, shows=True)) == WAITING
    assert said(look(MEERA, shows=True), look(ARJUN, shows=True)) == SEEN
    assert checked_state([look(MEERA, shows=True), look(ARJUN, shows=True)]).vision


def test_one_account_s_looks_never_agree_with_themselves() -> None:
    assert said(look(MEERA, shows=True), look(MEERA, shows=True)) == WAITING


def test_a_shows_from_an_account_that_publishes_at_once_marks_it_seen_alone() -> None:
    assert said(look(MEERA, shows=True, trusted=True)) == SEEN
    assert said() == WAITING


def test_a_refusal_hides_the_link_at_once_and_disagreement_waits_for_an_admin() -> None:
    alone = checked_state([look(MEERA, shows=False)])
    assert (alone.refused, alone.disputed, alone.vision) == (True, False, False)
    assert said(look(MEERA, shows=False)) == HIDDEN
    disputed = checked_state([look(MEERA, shows=True, trusted=True), look(ARJUN, shows=False)])
    assert (disputed.refused, disputed.disputed, disputed.vision) == (True, True, False)
    assert said(look(MEERA, shows=True, trusted=True), look(ARJUN, shows=False)) == IN_REVIEW


def test_an_admin_s_ruling_decides_both_ways_and_the_latest_one_holds() -> None:
    disputed = [look(MEERA, shows=True), look(ARJUN, shows=False)]
    assert said(*disputed, ruling(shows=True)) == SEEN
    assert checked_state([*disputed, ruling(shows=True)]).refused is False
    seen = [look(MEERA, shows=True, trusted=True)]
    assert said(*seen, ruling(shows=False)) == HIDDEN
    assert said(*seen, ruling(shows=False), ruling(shows=True)) == SEEN


def test_a_refused_link_is_never_served_and_the_picture_s_other_link_still_is() -> None:
    found = candidate(
        "wikimedia_commons", 1, "Ajrakh cloth printed in Dhamadka", licence="CC BY-SA 4.0", author="A"
    )
    seen = stored_picture(found, FACT, "VISION")
    refused = replace(seen, refused=True)
    other = stored_picture(found, OTHER_FACT)
    assert served_picture(seen, AJRAKH_WORLD) and served_picture(other, AJRAKH_WORLD)
    assert not served_picture(refused, AJRAKH_WORLD)
    (item,) = stored_items([refused, other], AJRAKH_WORLD)
    assert (item.media.id, item.claim_ids, item.relevance) == (other.media.id, [OTHER_FACT], "TEXT")


def test_a_picture_seen_by_a_person_is_served_before_one_chosen_by_its_words() -> None:
    worded = stored_picture(
        candidate("wikimedia_commons", 1, "Ajrakh printing", licence="CC BY-SA 4.0", author="A"), FACT
    )
    seen = stored_picture(
        candidate("wikimedia_commons", 2, "Ajrakh mordant", licence="CC BY-SA 4.0", author="B"),
        OTHER_FACT,
        "VISION",
    )
    items = stored_items([worded, seen], AJRAKH_WORLD)
    assert [(item.media.id, item.relevance) for item in items] == [
        (seen.media.id, "VISION"),
        (worded.media.id, "TEXT"),
    ]


def test_a_check_key_names_one_link_and_reserve_tasks_never_holds_it() -> None:
    link = uuid.UUID("0f6a1d2e-3b4c-4d5e-8f60-718293a4b5c6")
    assert TASK_KINDS.index(PICTURE_CHECK_TASK) == TASK_KINDS.index("MISSING_PICTURE") + 1
    assert PICTURE_CHECK_TASK in UNRESERVABLE_KINDS
    parsed = parse_task_key(check_key(link))
    assert (parsed.kind, parsed.detail, parsed.text()) == (PICTURE_CHECK_TASK, str(link), check_key(link))
    assert parse_task_key(PICTURE_CHECK_TASK).text() == PICTURE_CHECK_TASK


@pytest.mark.parametrize(
    "key",
    [
        "CHECK_PICTURES:not-a-link",
        "CHECK_PICTURES:craft:Ajrakh",
        "CHECK_PICTURES:0F6A1D2E-3B4C-4D5E-8F60-718293A4B5C6",
        "CHECK_PICTURES:0f6a1d2e-3b4c-4d5e-8f60-718293a4b5c6:more",
    ],
)
def test_a_check_key_that_names_no_link_is_refused(key: str) -> None:
    with pytest.raises(InvalidInput):
        parse_task_key(key)


async def test_reserve_tasks_refuses_a_check_key_before_it_reads_anything() -> None:
    no_session: Any = None
    for key in (PICTURE_CHECK_TASK, check_key(uuid.UUID(int=5))):
        with pytest.raises(InvalidInput, match=CHECKS_NOT_RESERVED):
            await claim_task(no_session, MEERA, key, site="https://kalavigyan.example", now=datetime.now(UTC))


async def test_the_check_task_is_listed_only_when_no_one_page_is_asked_for() -> None:
    no_session: Any = None
    assert await picture_check_tasks(no_session, WorkFilters(craft_slug="Ajrakh")) == []
    assert await picture_check_tasks(no_session, WorkFilters(category_slug="Textiles")) == []
