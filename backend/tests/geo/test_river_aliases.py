import copy
from typing import Any

import pytest

from app.data.map_layers import held_river_names
from app.data.river_aliases import RIVER_ALIASES_CODE, load_river_aliases, parse_river_aliases
from app.services.map_layer_places import RIVER_UNHELD, held_water_problems

JAIPUR = 102
DRAVYAVATI = "Dravyavati"
JDA_QUOTE = (
    "Dravyavati River was the active river of Jaipur which, over the time turned into a Nallah "
    "(Amanisha Nallah) due to rapid urbanization & industrialization on both side of the river."
)
PAPER_DOI = "10.5897/JGRP2017.0620"


def _source(quote: str) -> dict[str, Any]:
    return {
        "title": "A report on the river",
        "authors": [],
        "publisher": "A district authority",
        "year": 2017,
        "url": "https://example.gov.in/report.pdf",
        "doi": None,
        "grade": "A",
        "quote": quote,
        "locator": "page 2",
        "retrievedAt": "2026-11-26",
    }


def _body(**alias: Any) -> dict[str, Any]:
    row = {
        "id": "dravyavati",
        "names": ["Dravyavati River", "Amanisha Nallah"],
        "districtLgds": [JAIPUR],
        "sources": [_source(JDA_QUOTE)],
    }
    return {"schemaVersion": 1, "register": {"code": RIVER_ALIASES_CODE}, "aliases": [row | alias]}


def test_the_register_records_the_dravyavati_and_the_amanishah_nallah_as_one_river_with_their_sources() -> (
    None
):
    [alias] = load_river_aliases()
    assert alias.ref == "RIVER_ALIASES:dravyavati"
    assert alias.names == ("Dravyavati River", "Amanisha Nallah", "Dravayawati River", "Amanishah Nala")
    assert alias.district_lgds == frozenset({JAIPUR})
    assert [source.grade for source in alias.sources] == ["A", "A"]
    assert alias.sources[0].quote == JDA_QUOTE
    assert alias.sources[0].url.startswith("https://environmentclearance.nic.in/")
    assert alias.sources[1].doi == PAPER_DOI
    assert len({source.publisher for source in alias.sources}) == 2


def test_a_well_cited_alias_parses_and_each_name_is_quoted() -> None:
    [alias] = parse_river_aliases(_body())
    assert alias.names == ("Dravyavati River", "Amanisha Nallah")
    assert alias.sources[0].retrieved_at == "2026-11-26"


def test_an_alias_without_a_source_is_refused_by_its_id() -> None:
    with pytest.raises(ValueError, match="'dravyavati' cites no source"):
        parse_river_aliases(_body(sources=[]))
    with pytest.raises(ValueError, match="cites no source"):
        parse_river_aliases(_body(sources=None))


def test_a_quote_that_names_one_river_or_leaves_a_name_unstated_is_refused() -> None:
    with pytest.raises(ValueError, match="quotes 1 of its names"):
        parse_river_aliases(_body(sources=[_source("Dravyavati River was the active river of Jaipur.")]))
    with pytest.raises(ValueError, match="names 'Saraswati', which no quote"):
        parse_river_aliases(_body(names=["Dravyavati River", "Amanisha Nallah", "Saraswati"]))


def test_a_source_without_its_address_grade_or_quote_is_refused() -> None:
    for key, value, match in (
        ("url", "http://example.gov.in/report.pdf", "over https"),
        ("grade", "E", "its grade"),
        ("locator", "", "gives no locator"),
    ):
        body = _body()
        broken = copy.deepcopy(body)
        broken["aliases"][0]["sources"][0][key] = value
        with pytest.raises(ValueError, match=match):
            parse_river_aliases(broken)


def test_one_name_and_a_repeated_id_are_refused() -> None:
    with pytest.raises(ValueError, match="at least 2 rivers"):
        parse_river_aliases(_body(names=["Dravyavati River"]))
    twice = _body()
    twice["aliases"] = twice["aliases"] * 2
    with pytest.raises(ValueError, match="an id of its own"):
        parse_river_aliases(twice)


def test_a_map_names_the_dravyavati_through_its_cited_alias_and_an_unrecorded_name_is_refused() -> None:
    assert {DRAVYAVATI, "Dravyavati River", "Amanisha River", "Amanishah Nala"} <= held_river_names()
    assert held_water_problems([DRAVYAVATI], []) == []
    assert held_water_problems(["Saraswati of Sanganer"], []) == [
        RIVER_UNHELD.format(name="Saraswati of Sanganer")
    ]
