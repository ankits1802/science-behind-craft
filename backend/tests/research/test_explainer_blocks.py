from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from app.research.explainer import BLOCK_MODELS, BUILT_BLOCK_KINDS, Block

from ..contracts.phase_b_golden import phase_b_blocks
from ..contracts.phase_c_golden import phase_c_blocks
from ..contracts.phase_d_golden import phase_d_blocks
from .signature_fixtures import SIGNATURE_DECLARED

CLAIM = "826c1d72-9373-59f0-85c3-6bb38aa89320"
SOURCE = "d0f53ee9-4b97-5df7-a367-686957bdb7c8"
ENVELOPE = frozenset({"id", "kind", "version", "reuse"})
CRAFTS = [
    {"slug": "Kutch-Ajrakh", "name": "Kutch Ajrakh", "path": "/crafts/Kutch-Ajrakh"},
    {
        "slug": "Bagru-Hand-Block-Print",
        "name": "Bagru Hand Block Print",
        "path": "/crafts/Bagru-Hand-Block-Print",
    },
]


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
    "in_practice": {"notes": [{"audience": "NGO", "sentences": [sentence()]}]},
    "open_questions": {
        "items": [{"sentence": sentence(level="HYPOTHESIS"), "howToFindOut": "Test the wash water."}]
    },
    "artisan_voice": {
        "version": 2,
        "removed": 0,
        "quotes": [
            {
                "itemId": "FIELD_REPOSITORY:media-1:turn-1",
                "origin": "FIELD_REPOSITORY",
                "speaker": {
                    "name": "A. Artisan",
                    "line": "A. Artisan",
                    "role": "ARTISAN",
                    "yearsInCraft": 31,
                    "district": "District A",
                    "state": "State A",
                },
                "quote": "A quoted line from the recording.",
                "language": "gu",
                "english": "A quoted line from the recording.",
                "englishSource": "MACHINE",
                "sourceId": SOURCE,
                "locator": "12:04–12:31",
                "workshop": "a workshop in District A, State A, March 2026",
                "recordedOn": "2026-03-14",
                "corroboratedBy": [],
            }
        ],
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

DECLARED |= {
    block["kind"]: {key: value for key, value in block.items() if key not in ENVELOPE}
    for block in [*phase_b_blocks().values(), *phase_c_blocks().values(), *phase_d_blocks().values()]
    if block["kind"] not in BUILT_BLOCK_KINDS
}
DECLARED |= SIGNATURE_DECLARED
BLOCK = TypeAdapter(Block)


def declared(kind: str, **changes: Any) -> dict[str, Any]:
    return envelope(kind) | DECLARED[kind] | changes


def test_every_kind_not_built_yet_is_declared_here() -> None:
    assert set(DECLARED) == set(BLOCK_MODELS) - set(BUILT_BLOCK_KINDS)


@pytest.mark.parametrize("kind", sorted(DECLARED))
def test_each_declared_kind_validates_inside_the_one_envelope(kind: str) -> None:
    block = BLOCK.validate_python(declared(kind))
    version = DECLARED[kind].get("version", 1)
    assert (block.kind, block.version, block.reuse) == (kind, version, None)
    assert type(block) is BLOCK_MODELS[kind]
    assert block.cited_source_ids() or block.cites_datasets()
    with pytest.raises(ValidationError):
        BLOCK.validate_python(declared(kind, version=version + 1))


@pytest.mark.parametrize(
    ("kind", "changes", "message"),
    [
        (
            "artisan_voice",
            {"quotes": [{**DECLARED["artisan_voice"]["quotes"][0], "quote": "Call 98250 12345 67."}]},
            "phone",
        ),
        (
            "artisan_voice",
            {"quotes": [], "removed": 0},
            "quotes nobody",
        ),
        (
            "artisan_voice",
            {"quotes": [{**DECLARED["artisan_voice"]["quotes"][0], "englishSource": None}]},
            "come together",
        ),
        ("quiz", {"questions": [{**DECLARED["quiz"]["questions"][0], "answer": 5}]}, "keys one of"),
        ("open_questions", {"items": [{"sentence": sentence(), "howToFindOut": None}]}, "is a hypothesis"),
        (
            "open_questions",
            {"items": [{"sentence": sentence(level="HYPOTHESIS"), "howToFindOut": "Test 3 wells."}]},
            "no figures",
        ),
    ],
)
def test_declared_kinds_keep_their_rules(kind: str, changes: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        BLOCK.validate_python(declared(kind, **changes))
