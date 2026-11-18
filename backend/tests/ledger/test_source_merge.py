from typing import Any

from app.services.source_merge import SourceMerge, source_keys

from .indigo_claims import (
    EDWARDS,
    EDWARDS_JOURNAL,
    FRATER_BOOK,
    FRATER_WEB,
    GI_COPY,
    GI_JOURNAL,
    IMPART,
    KHAMIR_ART,
    KHAMIR_PART,
    source,
)


def merged(*refs: dict[str, Any]) -> SourceMerge:
    merge = SourceMerge()
    for ref in refs:
        merge.register(ref["id"], ref)
    return merge


def test_a_doi_in_its_field_and_in_a_doi_link_name_one_work() -> None:
    linked = source("linked", "PAPER", "Ajrakh dress", url="https://doi.org/10.1080/00404969.2016.1211436")
    merge = merged(EDWARDS, EDWARDS_JOURNAL, linked)
    assert {merge.canonical(ref["id"]) for ref in (EDWARDS, EDWARDS_JOURNAL, linked)} == {EDWARDS["id"]}


def test_one_address_with_or_without_www_and_a_closing_slash_is_one_source() -> None:
    merge = merged(KHAMIR_PART, KHAMIR_ART)
    assert merge.canonical(KHAMIR_ART["id"]) == KHAMIR_PART["id"]


def test_a_title_in_other_words_order_with_asides_is_one_source() -> None:
    merge = merged(GI_COPY, GI_JOURNAL)
    assert merge.canonical(GI_JOURNAL["id"]) == GI_COPY["id"]
    assert list(merge.refs()) == [GI_COPY["id"]]


def test_a_merged_source_keeps_the_first_title_the_earliest_year_and_fills_what_it_lacked() -> None:
    merge = merged(FRATER_WEB, FRATER_BOOK)
    (ref,) = merge.refs().values()
    assert (ref["id"], ref["title"], ref["kind"]) == (FRATER_WEB["id"], FRATER_WEB["title"], "WEB_PAGE")
    assert (ref["year"], ref["authors"]) == (2024, ["Judy Frater"])


def test_a_short_title_alone_never_merges_two_works() -> None:
    wikipedia = source("wikipedia", "ENCYCLOPEDIA", "Ajrakh", url="https://en.wikipedia.org/wiki/Ajrakh")
    merge = merged(IMPART, wikipedia)
    assert merge.canonical(wikipedia["id"]) == wikipedia["id"]
    assert source_keys(wikipedia) == ["url:en.wikipedia.org/wiki/Ajrakh"]


def test_two_papers_with_one_title_but_different_dois_stay_apart() -> None:
    title = "A survey of natural dyes used in Indian textile printing"
    first = source("first", "PAPER", title, doi="10.1000/one")
    second = source("second", "PAPER", title, doi="10.1000/two")
    merge = merged(first, second)
    assert merge.canonical(second["id"]) == second["id"]


def test_two_works_sharing_a_title_but_stating_different_years_stay_apart() -> None:
    title = "Annual Report of the Archaeological Survey of India"
    early = source("asi-1905", "GOVERNMENT_REPORT", title, url="https://example.org/asi-1905.pdf", year=1905)
    late = source("asi-1930", "GOVERNMENT_REPORT", title, url="https://example.org/asi-1930.pdf", year=1930)
    merge = merged(early, late)
    assert merge.canonical(late["id"]) == late["id"]
    assert {ref["year"] for ref in merge.refs().values()} == {1905, 1930}


def test_one_address_still_merges_two_records_that_state_different_years() -> None:
    merge = merged(FRATER_WEB, FRATER_BOOK)
    assert (FRATER_WEB["year"], FRATER_BOOK["year"]) == (2025, 2024)
    assert merge.canonical(FRATER_BOOK["id"]) == FRATER_WEB["id"]


def test_a_source_known_only_by_its_id_maps_to_itself() -> None:
    merge = SourceMerge()
    assert merge.register("unknown", None) == "unknown"
    assert merge.refs() == {}


def test_every_source_id_in_a_payload_is_remapped() -> None:
    merge = merged(GI_COPY, GI_JOURNAL)
    payload = {
        "citations": [{"sourceId": GI_JOURNAL["id"]}],
        "media": {"sourceId": None},
        "x": [GI_JOURNAL["id"]],
    }
    assert merge.remapped(payload) == {
        "citations": [{"sourceId": GI_COPY["id"]}],
        "media": {"sourceId": None},
        "x": [GI_JOURNAL["id"]],
    }
