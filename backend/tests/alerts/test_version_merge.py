import pytest
from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.services.version_merge import merged_version

from .versions import base_version, first_explainer, follow_up_document, latest_golden


def water_and_history() -> list[dict]:
    latest = latest_golden()["explainer"]
    water, history = latest["sections"][1], latest["sections"][3]
    return [{**water, "blocks": [water["blocks"][1]]}, history]


def test_a_follow_up_is_merged_into_the_fixture_s_second_version() -> None:
    merged = merged_version(base_version(), follow_up_document(water_and_history()))
    expected = latest_golden()
    assert merged.explainer.model_dump(mode="json", by_alias=True) == expected["explainer"]
    assert merged.mark.model_dump(mode="json", by_alias=True) == expected["mark"]


def test_merging_leaves_the_version_it_builds_on_untouched() -> None:
    base = base_version()
    before = base.model_dump(mode="json", by_alias=True)
    merged_version(base, follow_up_document(water_and_history()))
    assert base.model_dump(mode="json", by_alias=True) == before
    assert base.explainer == first_explainer()


def test_pictures_stay_last_when_a_section_with_pictures_is_deepened() -> None:
    latest = latest_golden()["explainer"]
    added = {**latest["sections"][1]["blocks"][1], "id": "s1.b3"}
    for n, sentence in enumerate(added["sentences"], start=1):
        sentence["id"] = f"s1.b3.{n}"
    process = {**latest["sections"][0], "blocks": [added]}
    merged = merged_version(base_version(), follow_up_document([process]))
    assert [block.id for block in merged.explainer.sections[0].blocks] == ["s1.b1", "s1.b3", "s1.b2"]
    assert [change.block_ids for change in merged.mark.changes] == [["s1.b3"]]


def test_an_empty_added_section_is_left_out_and_later_ones_keep_their_order() -> None:
    history = water_and_history()[1]
    empty = {**history, "id": "s4", "discipline": "ECONOMICS", "title": "Economics", "state": "EMPTY"}
    empty |= {"blocks": [], "searched": "Searched stored findings and two live queries."}
    moved = {**history, "id": "s5"}
    moved["blocks"] = [{**moved["blocks"][0], "id": "s5.b1"}]
    for n, sentence in enumerate(moved["blocks"][0]["sentences"], start=1):
        sentence["id"] = f"s5.b1.{n}"
    merged = merged_version(base_version(), follow_up_document([empty, moved]))
    assert [(s.id, s.order) for s in merged.explainer.sections] == [
        ("s1", 1),
        ("s2", 2),
        ("s3", 3),
        ("s5", 4),
    ]
    assert [(c.section_id, c.change) for c in merged.mark.changes] == [("s5", "ADDED")]


def test_a_follow_up_that_reuses_a_block_id_the_explainer_showed_is_refused() -> None:
    latest = latest_golden()["explainer"]
    clash = {**latest["sections"][1], "blocks": [{**latest["sections"][1]["blocks"][1], "id": "s2.b1"}]}
    with pytest.raises((InvalidInput, ValidationError)):
        merged_version(base_version(), follow_up_document([clash]))
