from typing import Any

import pytest

from app.core.errors import ExternalFailure
from app.sources.reference.wikidata_places import (
    COORDINATES_IDS_MAX,
    PlaceCandidate,
    PlacePoint,
    coordinates_from_bindings,
    coordinates_query,
)

from .recorded import WIKIDATA_API, WIKIDATA_SPARQL, Reply, wikidata_adapter

SHIKARPUR_SINDH = PlaceCandidate(
    "Q1250069", "Shikarpur", "city and the capital of Shikarpur District in Sindh province of Pakistan"
)
PETHAPUR = PlaceCandidate("Q2764770", "Pethapur", "village in Gujarat state, India")
EXACT_SHIKARPURS = [
    "Q1250069",
    "Q60793837",
    "Q105772812",
    "Q60819252",
    "Q60454221",
    "Q60804269",
    "Q7496551",
    "Q60454382",
    "Q60818097",
]


def binding(item: str, point: str, rank: str = "NormalRank") -> dict[str, Any]:
    return {
        "item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{item}"},
        "coordinates": {"type": "literal", "value": point},
        "rank": {"type": "uri", "value": f"http://wikiba.se/ontology#{rank}"},
    }


async def test_a_place_search_keeps_only_items_whose_label_or_alias_is_the_name() -> None:
    adapter, recorder = wikidata_adapter(
        {
            WIKIDATA_API: [
                Reply("wikidata_places_shikarpur.json"),
                Reply("wikidata_places_dhamadka.json"),
                Reply("wikidata_places_pethapur.json"),
            ]
        }
    )
    shikarpur = await adapter.place_candidates("Shikarpur")
    assert [candidate.item_id for candidate in shikarpur] == EXACT_SHIKARPURS
    assert shikarpur[0] == SHIKARPUR_SINDH
    assert await adapter.place_candidates("Dhamadka") == []
    assert await adapter.place_candidates(" pethapur ") == [PETHAPUR]
    first = recorder.requests[0].url
    assert (first.scheme, first.host, first.path) == ("https", "www.wikidata.org", "/w/api.php")
    assert dict(first.params) | {"search": "Shikarpur"} == {
        "format": "json",
        "formatversion": "2",
        "errorformat": "plaintext",
        "action": "wbsearchentities",
        "search": "Shikarpur",
        "language": "en",
        "uselang": "en",
        "type": "item",
        "limit": "10",
    }
    assert recorder.requests[2].url.params["search"] == "pethapur"


async def test_coordinates_are_read_from_one_sparql_query() -> None:
    adapter, recorder = wikidata_adapter({WIKIDATA_SPARQL: Reply("wikidata_place_points.json")})
    points = await adapter.place_points(["Q1250069", "Q2764770"])
    assert points == {
        "Q1250069": PlacePoint(latitude=28.0, longitude=68.666666666),
        "Q2764770": PlacePoint(latitude=23.2908, longitude=72.6386),
    }
    (request,) = recorder.requests
    assert (request.url.host, request.url.path) == ("query.wikidata.org", "/sparql")
    assert "VALUES ?item { wd:Q1250069 wd:Q2764770 }" in request.url.params["query"]
    assert "p:P625" in request.url.params["query"]
    assert request.headers["accept"] == "application/sparql-results+json"


async def test_a_failed_place_search_is_an_external_failure() -> None:
    adapter, _ = wikidata_adapter({WIKIDATA_API: Reply("wikidata_entity_missing.json", status=503)})
    with pytest.raises(ExternalFailure):
        await adapter.place_candidates("Shikarpur")


def test_a_preferred_coordinate_wins_and_a_deprecated_one_is_never_read() -> None:
    bindings = [
        binding("Q1", "Point(70.0 23.0)"),
        binding("Q1", "Point(70.5 23.5)", "PreferredRank"),
        binding("Q2", "Point(71.0 22.0)", "DeprecatedRank"),
        binding("Q2", "Point(71.25 22.25)"),
    ]
    assert coordinates_from_bindings(bindings) == {
        "Q1": PlacePoint(latitude=23.5, longitude=70.5),
        "Q2": PlacePoint(latitude=22.25, longitude=71.25),
    }


def test_two_different_coordinates_of_one_rank_place_nothing() -> None:
    bindings = [binding("Q3", "Point(70.0 23.0)"), binding("Q3", "Point(72.0 21.0)")]
    assert coordinates_from_bindings(bindings) == {}
    same = [binding("Q4", "Point(70.0 23.0)"), binding("Q4", "Point(70.0 23.0)")]
    assert coordinates_from_bindings(same) == {"Q4": PlacePoint(latitude=23.0, longitude=70.0)}


@pytest.mark.parametrize(
    "literal",
    [
        "<http://www.wikidata.org/entity/Q405> Point(23.47 0.67)",
        "Point(190.0 23.0)",
        "Point(70.0 -91.0)",
        "Point(70.0)",
        "",
    ],
)
def test_only_earth_points_in_range_are_read(literal: str) -> None:
    assert coordinates_from_bindings([binding("Q5", literal)]) == {}


def test_the_coordinates_query_takes_item_ids_only() -> None:
    with pytest.raises(ValueError, match="not Wikidata item ids"):
        coordinates_query(["Q1", "Q1 } . ?x ?y ?z"])
    with pytest.raises(ValueError, match="1 to"):
        coordinates_query([])
    with pytest.raises(ValueError, match="1 to"):
        coordinates_query([f"Q{n}" for n in range(1, COORDINATES_IDS_MAX + 2)])
