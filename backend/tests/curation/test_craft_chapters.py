from __future__ import annotations

import json
from collections import Counter
from typing import Any

import pytest

from app.data.craft_text import fold
from app.research.chapter_keys import CHAPTER_KEYS
from app.research.craft_page import CraftPage
from app.research.craft_page_checks import shown_pictures
from app.services.chapter_preview import PREVIEW_SITE
from app.services.curation_keys import curated_id

from ..contracts.golden import golden_json
from .import_support import AJRAKH_GOLDEN, raw

REGISTER_GOLDEN = "craft.page.register.golden.json"
INPUTS = "craft.page.inputs.json"
AJRAKH = "Kutch-Ajrakh"
KACHCHH = 449
REGISTER_CHAPTERS = ["glance", "kin", "sources"]
SEASON_LABELS = {"Monsoon", "Winter", "Summer"}


@pytest.fixture(scope="module")
def ajrakh() -> CraftPage:
    return CraftPage.model_validate(golden_json(AJRAKH_GOLDEN))


@pytest.fixture(scope="module")
def register() -> CraftPage:
    return CraftPage.model_validate(golden_json(REGISTER_GOLDEN))


def items(page: CraftPage, chapter: str, kind: str) -> list[Any]:
    found = [item for c in page.chapters if c.key == chapter for item in c.items if item.kind == kind]
    return [item.block if item.block is not None else item.part for item in found]


def test_chapters_keep_the_monograph_order_and_none_is_empty(ajrakh: CraftPage, register: CraftPage) -> None:
    for page in (ajrakh, register):
        keys = [chapter.key for chapter in page.chapters]
        assert keys == [key for key in CHAPTER_KEYS if key in keys]
        assert all(chapter.items for chapter in page.chapters)


def test_no_sentence_text_appears_twice_on_the_page(ajrakh: CraftPage) -> None:
    texts = [fold(sentence.text) for chapter in ajrakh.chapters for sentence in chapter.sentences()]
    texts += [fold(sentence.text) for sentence in ajrakh.lede]
    repeated = [text for text, count in Counter(texts).items() if count > 1]
    assert repeated == []


def test_no_picture_appears_twice(ajrakh: CraftPage) -> None:
    pictures = list(shown_pictures(ajrakh))
    assert len({media.id for media in pictures}) == len(pictures)
    assert len({media.image_url for media in pictures}) == len(pictures)


def test_every_dossier_picture_is_shown_once(ajrakh: CraftPage) -> None:
    shown = {media.page_url for media in shown_pictures(ajrakh)}
    assert shown == {picture["pageUrl"] for picture in raw(AJRAKH)["pictures"]}


def test_the_masthead_carries_the_placed_picture_and_the_craft_s_own_name(ajrakh: CraftPage) -> None:
    (placed,) = [p for p in raw(AJRAKH)["pictures"] if (p.get("placement") or {}).get("role") == "MASTHEAD"]
    assert ajrakh.masthead.picture is not None and ajrakh.masthead.picture.media.page_url == placed["pageUrl"]
    assert ajrakh.masthead.place == "Kachchh, Gujarat"
    assert ajrakh.masthead.gi is not None and ajrakh.masthead.gi.status == "REGISTERED"
    names = raw(AJRAKH).get("nativeNames") or []
    assert ajrakh.masthead.native_name is not None and ajrakh.masthead.native_name.text == names[0]["text"]


def test_the_chemistry_plays_the_reactions_with_the_family_s_steps_marked_borrowed(ajrakh: CraftPage) -> None:
    (chem,) = [chapter for chapter in ajrakh.chapters if chapter.key == "chem"]
    (item,) = [item for item in chem.items if item.kind == "reaction_player"]
    steps = item.block.steps
    assert [step.stage for step in steps if step.stage_id is not None] == [
        "Iron-black printing",
        "Indigo dyeing",
    ]
    borrowed = [step for step in steps if step.stage_id is None]
    assert borrowed and all("indigo" in step.label for step in borrowed)
    assert item.figure is not None and [b.scope for b in item.figure.borrowed] == ["FAMILY"]
    assert {source.group for source in ajrakh.sources} >= {"FAMILY", "COMPOUND_RECORDS"}


def test_every_compound_with_a_cid_and_a_kept_conformer_has_its_molecule(ajrakh: CraftPage) -> None:
    kept = set(golden_json(INPUTS)["conformers"])
    cids = {m["pubchemCid"] for m in raw(AJRAKH)["materials"] if m.get("pubchemCid")}
    assert {block.pubchem_cid for block in items(ajrakh, "chem", "molecule_3d")} == cids & kept
    assert items(ajrakh, "chem", "material_card")


def test_every_curated_stage_is_on_the_ladder(ajrakh: CraftPage) -> None:
    (ladder,) = items(ajrakh, "made", "process_ladder")
    assert [stage.name for stage in ladder.stages] == [stage["name"] for stage in raw(AJRAKH)["stages"]]
    assert ajrakh.depth.stages == len(ladder.stages)


def test_every_ladder_stage_shows_its_stated_colour(ajrakh: CraftPage) -> None:
    (ladder,) = items(ajrakh, "made", "process_ladder")
    stated = {
        stage["name"]: stage["after"]["colours"] for stage in raw(AJRAKH)["stages"] if stage.get("after")
    }
    shown = {stage.name: list(stage.after.colours) for stage in ladder.stages if stage.after is not None}
    assert stated and all(shown.get(name) == colours for name, colours in stated.items())


def test_each_stage_s_why_is_the_dossier_s_or_absent(ajrakh: CraftPage) -> None:
    (ladder,) = items(ajrakh, "made", "process_ladder")
    dossier = {stage["name"]: stage.get("whyClaimId") for stage in raw(AJRAKH)["stages"]}
    for stage in ladder.stages:
        named = dossier[stage.name]
        shown = {citation.claim_id for sentence in stage.sentences for citation in sentence.citations}
        cited = [citation.claim_id for citation in stage.why.citations] if stage.why else []
        if named is None:
            continue
        wanted = str(curated_id(AJRAKH, named))
        assert cited == [] if wanted in shown else set(cited) == {wanted}, stage.name


def test_why_kachchh_tells_the_region_its_climate_and_its_seasons(ajrakh: CraftPage) -> None:
    (chapter,) = [chapter for chapter in ajrakh.chapters if chapter.key == "why"]
    assert chapter.title == "Why Kachchh" and chapter.opener is not None
    (story,) = items(ajrakh, "why", "region_story")
    assert [district.district_lgd for district in story.districts] == [KACHCHH]
    (climate,) = items(ajrakh, "why", "climate_risk")
    assert {len(series.values) for series in climate.series} == {45}
    (seasons,) = items(ajrakh, "why", "seasons")
    staged = {stage.name for stage in items(ajrakh, "made", "process_ladder")[0].stages}
    assert all(row.label in staged or row.label in SEASON_LABELS or row.months for row in seasons.rows)
    monsoon = [row for row in seasons.rows if row.sentence.text.startswith("With the onset of the monsoon")]
    assert [(row.label, row.season) for row in monsoon] == [("Monsoon", "MONSOON")]


def test_history_draws_a_timeline_and_market_the_gi_record(ajrakh: CraftPage) -> None:
    (timeline,) = items(ajrakh, "history", "timeline_map")
    names = [place.name for place in timeline.places]
    assert [(names[route.start], names[route.end]) for route in timeline.routes] == [("Sindh", "Kutch")]
    assert (timeline.routes[0].year_from, timeline.routes[0].year_to) == (1586, 1631)
    assert timeline.points and all(names[point.place] != "Sindh" for point in timeline.points)
    placed = {place.name for place in timeline.places if place.latitude is not None}
    assert placed == {place["name"] for place in raw(AJRAKH)["places"] if place.get("wikidataId")}
    (record,) = items(ajrakh, "history", "record")
    assert record.entries[0].label == "11th to 14th century"
    (market,) = items(ajrakh, "market", "market_gi")
    assert (
        market.gi is not None
        and market.gi.application_number == raw(AJRAKH)["market"]["gi"]["applicationNumber"]
    )


def test_people_and_kin_carry_the_communities_and_the_family(ajrakh: CraftPage) -> None:
    assert items(ajrakh, "people", "communities")
    (relatives,) = items(ajrakh, "kin", "relatives")
    assert (
        relatives.family is not None and relatives.family.path == "/categories/Textiles-Based-Craft-Category"
    )


def test_sources_are_numbered_once_in_reading_order_with_their_groups(ajrakh: CraftPage) -> None:
    (listing,) = items(ajrakh, "sources", "source_list")
    grouped = [source_id for group in listing.groups for source_id in group.source_ids]
    assert sorted(grouped) == sorted(source.id for source in ajrakh.sources)
    first = [c.source_id for c in (ajrakh.masthead.gi.citations if ajrakh.masthead.gi else [])]
    assert [source.id for source in ajrakh.sources][: len(dict.fromkeys(first))] == list(dict.fromkeys(first))


def test_cite_this_names_the_versioned_address(ajrakh: CraftPage) -> None:
    assert ajrakh.cite is not None
    path = f"/crafts/kutch-ajrakh/v{raw(AJRAKH)['version']}"
    assert ajrakh.cite.url == path
    assert ajrakh.cite.text.endswith(f" {PREVIEW_SITE}{path}")
    assert ajrakh.cite.bibtex.startswith("@misc{")
    assert f"howpublished = {{\\url{{{PREVIEW_SITE}{path}}}}}" in ajrakh.cite.bibtex


def test_the_hero_is_the_masthead_picture(ajrakh: CraftPage, register: CraftPage) -> None:
    (hero,) = [picture for picture in ajrakh.pictures if picture.role == "HERO"]
    assert ajrakh.masthead.picture is not None and hero.media.id == ajrakh.masthead.picture.media.id
    (relatives,) = items(register, "kin", "relatives")
    (kin,) = [craft for craft in relatives.crafts if craft.craft.slug == AJRAKH]
    assert kin.hero is not None and kin.hero.media.page_url == ajrakh.masthead.picture.media.page_url


def test_the_family_group_keeps_the_family_s_label(ajrakh: CraftPage) -> None:
    (listing,) = items(ajrakh, "sources", "source_list")
    assert "From the Textiles family monograph" in [group.title for group in listing.groups]


def test_a_craft_without_a_dossier_shows_only_the_chapters_it_has(register: CraftPage) -> None:
    assert [chapter.key for chapter in register.chapters] == REGISTER_CHAPTERS
    (facts,) = items(register, "glance", "register_facts")
    assert {fact.label for fact in facts.facts} >= {"Family", "Kind"}
    (start,) = items(register, "glance", "start_research")
    assert start.questions == register.suggested_questions
    assert register.craft.family_label == "Textiles"
    assert register.cite is None and register.masthead.picture is None
    assert register.masthead.provenance.basis == "REGISTER"


def test_the_kin_sources_of_a_page_name_their_monograph(register: CraftPage) -> None:
    kin = [source for source in register.sources if source.group == "KIN"]
    assert kin and {source.from_.slug for source in kin if source.from_} == {AJRAKH}


def test_the_golden_carries_no_user_or_answer_id(ajrakh: CraftPage) -> None:
    text = json.dumps(golden_json(AJRAKH_GOLDEN))
    for key in ("userId", "answerId", "askedBy", "requestedById", "createdById"):
        assert f'"{key}"' not in text
