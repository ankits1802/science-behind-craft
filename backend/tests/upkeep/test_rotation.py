import pytest

from app.services.upkeep_pages import MONOGRAPHS_PER_NIGHT, PAGES_PER_NIGHT, rotating_window

SLUGS = ["a", "b", "c", "d", "e"]


def test_every_item_is_taken_when_the_window_holds_them_all() -> None:
    assert rotating_window(SLUGS, 5, 739_000) == SLUGS
    assert rotating_window([], 3, 739_000) == []


@pytest.mark.parametrize(
    ("night", "expected"),
    [(0, ["a", "b"]), (1, ["c", "d"]), (2, ["e", "a"]), (3, ["b", "c"]), (5, ["a", "b"])],
)
def test_the_window_moves_on_each_night_and_wraps(night: int, expected: list[str]) -> None:
    assert rotating_window(SLUGS, 2, night) == expected


def test_five_nights_of_two_reach_every_item_twice() -> None:
    seen = [slug for night in range(5) for slug in rotating_window(SLUGS, 2, night)]
    assert sorted(seen) == sorted(SLUGS * 2)


def test_a_window_holds_at_least_one_item() -> None:
    with pytest.raises(ValueError, match="at least one"):
        rotating_window(SLUGS, 0, 1)


def test_the_nightly_page_bounds() -> None:
    assert (MONOGRAPHS_PER_NIGHT, PAGES_PER_NIGHT) == (20, 60)
