from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from app.research.explainer import BLOCK_MODELS, BUILT_BLOCK_KINDS, Block

CLAIM = "826c1d72-9373-59f0-85c3-6bb38aa89320"
SOURCE = "d0f53ee9-4b97-5df7-a367-686957bdb7c8"
STAGE = "5ced8309-b0f4-571a-8482-4223d1d4fccc"
CRAFTS = [
    {"slug": "Kutch-Ajrakh", "name": "Kutch Ajrakh", "path": "/crafts/Kutch-Ajrakh"},
    {
        "slug": "Bagru-Hand-Block-Print",
        "name": "Bagru Hand Block Print",
        "path": "/crafts/Bagru-Hand-Block-Print",
    },
]
MEDIA = {
    "id": "a1c3e5f7-0b2d-4f6a-8c9e-1d3f5a7b9c0e",
    "display": "INLINE",
    "provider": "wikimedia_commons",
    "pageUrl": "https://commons.wikimedia.org/wiki/File:Ajrak_Printing_Materials_1.jpg",
    "imageUrl": "https://upload.wikimedia.org/wikipedia/commons/4/4e/Ajrak_Printing_Materials_1.jpg",
    "width": 4160,
    "height": 3120,
    "title": "Ajrak Printing Materials 1",
    "alt": "Sticky gums used during indigo printing.",
    "author": "SMarndi",
    "site": "Wikimedia Commons",
    "credit": None,
    "licence": "CC BY-SA 4.0",
    "licenceUrl": "https://creativecommons.org/licenses/by-sa/4.0",
    "sourceId": None,
    "retrievedAt": "2026-11-17T10:20:00Z",
}


def citation(level: str = "PROVISIONAL") -> dict[str, Any]:
    return {
        "id": "bf7fda76-2629-5609-ac54-d4c011fbb573",
        "claimId": CLAIM,
        "sourceId": SOURCE,
        "quote": "presence of iron in the water supply dulls and darkens the final result.",
        "locator": "GI Journal No. 188 copy (application 1050), PDF p. 8",
        "context": None,
        "evidence": "QUOTED",
        "level": level,
    }


def sentence(sentence_id: str = "b.1", level: str = "PROVISIONAL") -> dict[str, Any]:
    return {
        "id": sentence_id,
        "text": "Iron in the water dulls and darkens the final result.",
        "level": level,
        "citations": [citation(level)],
        "translated": False,
        "terms": [],
    }


def envelope(kind: str) -> dict[str, Any]:
    return {"id": "s1.b1", "kind": kind, "version": 1, "reuse": None}


DECLARED: dict[str, dict[str, Any]] = {
    "region_story": {
        "river": {"name": None, "datasetCode": "HYDRORIVERS_1_0", "reachIds": [1, 2]},
        "districts": [{"districtLgd": 101, "name": "District A", "stateName": "State A"}],
        "steps": [{"districtLgd": 101, "sentence": sentence()}],
        "layers": ["water-river-distance"],
        "boundaryCaption": "External boundaries of India as depicted by Survey of India.",
    },
    "map_layer": {
        "layer": "soil-ph",
        "layerVersion": "v1",
        "basis": "District mean of topsoil pH",
        "datasetCodes": ["SOILGRIDS_2_0"],
        "highlighted": [101],
        "boundaryCaption": "External boundaries of India as depicted by Survey of India.",
    },
    "reaction_player": {
        "steps": [
            {
                "reactionId": "d9643f49-fefc-5e3a-ad08-a5ae499a4161",
                "label": "Scrap iron dissolving into iron acetate",
                "equation": "Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2",
                "balanced": True,
                "level": "PROVISIONAL",
                "citations": [citation()],
            }
        ]
    },
    "material_card": {
        "materialId": None,
        "name": "Alum",
        "formula": None,
        "pubchemCid": None,
        "wikidataId": "Q1",
        "localNames": ["fatakdi"],
        "role": "MORDANT",
        "facts": [sentence()],
        "handling": [],
    },
    "molecule_3d": {"pubchemCid": 6293, "name": "Alizarin", "formula": "C14H8O4", "sourceId": SOURCE},
    "simulation": {
        "concept": "Iron darkening a madder red",
        "title": "Iron in the wash water",
        "model": "claude-sonnet",
        "createdAt": "2026-11-17T10:30:00Z",
        "html": "<!doctype html><title>x</title>",
        "htmlSha256": "0" * 64,
        "values": [{"key": "ironShare", "value": 1.0, "unit": "%", "citations": [citation()]}],
        "hidden": False,
    },
    "what_if": {
        "changed": "Wash water",
        "options": [
            {"label": "River water", "outcome": sentence()},
            {"label": "Well water", "outcome": None},
        ],
    },
    "timeline_map": {
        "points": [
            {
                "label": "Place A",
                "yearFrom": 2001,
                "yearTo": 2001,
                "wikidataId": "Q2",
                "latitude": 23.23,
                "longitude": 69.79,
                "sentence": sentence(),
            }
        ],
        "routes": [],
    },
    "zoom_story": {
        "levels": [
            {
                "level": "DISTRICT",
                "media": None,
                "districtLgd": 101,
                "pubchemCid": None,
                "sentence": sentence("z.1"),
            },
            {
                "level": "CLOTH",
                "media": MEDIA,
                "districtLgd": None,
                "pubchemCid": None,
                "sentence": sentence("z.2"),
            },
        ]
    },
    "expert_view": {
        "seat": "HYDROLOGIST",
        "take": [sentence()],
        "agreesWith": ["CHEMIST"],
        "differs": [{"seat": "HISTORIAN", "thisView": sentence("e.1"), "otherView": sentence("e.2")}],
    },
    "seasons": {
        "rows": [{"stageId": STAGE, "label": "Kut printing", "months": [10, 11, 12], "sentence": sentence()}],
        "rainfall": None,
    },
    "supply_map": {
        "links": [
            {
                "material": "Alum",
                "materialId": None,
                "origin": "Kutch",
                "wikidataId": None,
                "latitude": None,
                "longitude": None,
                "sentence": sentence(),
            }
        ]
    },
    "compare": {
        "crafts": CRAFTS,
        "rows": [{"aspect": "Mordant", "left": sentence(), "right": None}],
        "pieceIds": [],
    },
    "in_practice": {"notes": [{"audience": "NGO", "sentences": [sentence()]}]},
    "quiz": {
        "questions": [
            {
                "prompt": "What dulls the colours?",
                "options": ["Iron", "Alum"],
                "answer": 0,
                "explanation": sentence(),
            }
        ]
    },
    "open_questions": {
        "items": [{"sentence": sentence(level="HYPOTHESIS"), "howToFindOut": "Test the wash water."}]
    },
    "artisan_voice": {
        "quotes": [
            {
                "artisan": {
                    "name": "A. Artisan",
                    "credentials": ["Block printer"],
                    "village": "Village A",
                    "district": "District A",
                    "state": "State A",
                    "address": None,
                },
                "quote": "A quoted line from the recording.",
                "language": "en",
                "sourceId": SOURCE,
                "locator": "turn 4",
            }
        ]
    },
    "designs": {
        "designs": [
            {
                "id": "design-1",
                "title": "Ajrakh stole",
                "workshop": None,
                "madeOn": "2026-10",
                "url": "https://designer.example.org/designs/1",
                "image": None,
                "sourceId": SOURCE,
            }
        ]
    },
}

BLOCK = TypeAdapter(Block)


def declared(kind: str, **changes: Any) -> dict[str, Any]:
    return envelope(kind) | DECLARED[kind] | changes


def test_every_kind_not_built_yet_is_declared_here() -> None:
    assert set(DECLARED) == set(BLOCK_MODELS) - set(BUILT_BLOCK_KINDS)


@pytest.mark.parametrize("kind", sorted(DECLARED))
def test_each_declared_kind_validates_inside_the_one_envelope(kind: str) -> None:
    block = BLOCK.validate_python(declared(kind))
    assert (block.kind, block.version, block.reuse) == (kind, 1, None)
    assert type(block) is BLOCK_MODELS[kind]
    assert block.cited_source_ids() or block.cites_datasets()
    with pytest.raises(ValidationError):
        BLOCK.validate_python(declared(kind, version=2))


@pytest.mark.parametrize(
    ("kind", "changes", "message"),
    [
        (
            "artisan_voice",
            {"quotes": [{**DECLARED["artisan_voice"]["quotes"][0], "quote": "Call 98250 12345 67."}]},
            "phone",
        ),
        ("compare", {"crafts": [CRAFTS[0], CRAFTS[0]]}, "two different crafts"),
        ("quiz", {"questions": [{**DECLARED["quiz"]["questions"][0], "answer": 2}]}, "keys one of"),
        ("open_questions", {"items": [{"sentence": sentence(), "howToFindOut": None}]}, "is a hypothesis"),
        (
            "open_questions",
            {"items": [{"sentence": sentence(level="HYPOTHESIS"), "howToFindOut": "Test 3 wells."}]},
            "no figures",
        ),
        ("zoom_story", {"levels": DECLARED["zoom_story"]["levels"][::-1]}, "level by level"),
        (
            "timeline_map",
            {"routes": [{"start": 0, "end": 1, "sentence": sentence()}]},
            "two different listed points",
        ),
        ("expert_view", {"agreesWith": ["HYDROLOGIST"]}, "never its own"),
        (
            "region_story",
            {"steps": [{"districtLgd": 102, "sentence": sentence()}]},
            "only districts it lists",
        ),
        ("seasons", {"rows": [{**DECLARED["seasons"]["rows"][0], "months": [12, 1]}]}, "once each, in order"),
        ("map_layer", {"datasetCodes": []}, "at least 1"),
        ("simulation", {"html": "x" * (200 * 1024 + 1)}, "larger than"),
    ],
)
def test_declared_kinds_keep_their_rules(kind: str, changes: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        BLOCK.validate_python(declared(kind, **changes))


def test_supply_origins_are_placed_only_with_wikidata_coordinates() -> None:
    link = {**DECLARED["supply_map"]["links"][0], "latitude": 23.2, "longitude": 69.8}
    with pytest.raises(ValidationError, match="Wikidata coordinates"):
        BLOCK.validate_python(declared("supply_map", links=[link]))
    placed = BLOCK.validate_python(declared("supply_map", links=[link | {"wikidataId": "Q1"}]))
    assert placed.links[0].latitude == 23.2
