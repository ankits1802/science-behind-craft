from __future__ import annotations

import json
import re
from collections.abc import Collection, Iterable, Mapping
from pathlib import Path
from typing import Any

from app.data.monograph_files import CONTENT_FILE

__all__ = [
    "KIND_DATA",
    "MOLECULE_DATA",
    "READER_DATA",
    "READER_SCOPE",
    "REGION_DATA",
    "fragment_sentences",
    "kit_data",
    "merged_data",
    "monograph_data",
    "reader_data",
    "unit_sentences",
]

MOLECULE_DATA = "mol-data"
REGION_DATA = "rs-data"
READER_DATA = "kv-data"
READER_SCOPE = "rm"
KIND_DATA: Mapping[str, str] = {
    "molecule_3d": MOLECULE_DATA,
    "map_layer": REGION_DATA,
    "map_sequence": REGION_DATA,
    "timeline_map": REGION_DATA,
}
MONOGRAPH_SLUG = re.compile(r"^[A-Za-z0-9-]+$")
MOLECULES_KEY = "molecules"
CID_KEY = "cid"
GEOMETRY_KEY = "geometry"
GEOMETRY_RADIUS_KEY = "radius"
ATOMS_KEY, BONDS_KEY, RADIUS_KEY, MARKS_KEY = "atoms", "bonds", "R", "marks"
SENTENCES_KEY = "sents"
SOURCES_KEY = "sources"
NUMBER_KEY = "n"
SENTENCE_ID_KEY = "sid"
SENTENCE_ATTRIBUTE = re.compile(r'data-sid="([^"]+)"')


def monograph_data(root: Path, monograph: str) -> dict[str, Any]:
    if not MONOGRAPH_SLUG.fullmatch(monograph):
        return {}
    path = root / monograph / CONTENT_FILE
    if not path.is_file():
        return {}
    data = json.loads(path.read_bytes().decode("utf-8")).get("data")
    return data if isinstance(data, dict) else {}


def kit_data(data: Mapping[str, Any], kind: str, spec: Mapping[str, Any] | None) -> dict[str, Any]:
    key = KIND_DATA.get(kind)
    if key is None:
        return {}
    block = data.get(key)
    if key != MOLECULE_DATA or spec is None:
        return {} if block is None else {key: block}
    held = block if isinstance(block, Mapping) else {}
    found: dict[str, Any] = {}
    for molecule in spec.get(MOLECULES_KEY, []):
        if not isinstance(molecule, Mapping):
            continue
        cid, geometry = str(molecule.get(CID_KEY)), molecule.get(GEOMETRY_KEY)
        if isinstance(geometry, Mapping):
            found[cid] = _turned_model(geometry)
        elif cid in held:
            found[cid] = held[cid]
    return {key: found} if found else {}


def _turned_model(geometry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        ATOMS_KEY: geometry.get(ATOMS_KEY, []),
        BONDS_KEY: geometry.get(BONDS_KEY, []),
        RADIUS_KEY: geometry.get(GEOMETRY_RADIUS_KEY),
        MARKS_KEY: [],
    }


def reader_data(
    data: Mapping[str, Any], sentences: Collection[str], numbers: Mapping[int, int]
) -> dict[str, Any]:
    block = data.get(READER_DATA)
    if not isinstance(block, Mapping):
        return {}
    held = block.get(SENTENCES_KEY) or {}
    listed = block.get(SOURCES_KEY) or {}
    sents = {
        sid: [
            {**item, NUMBER_KEY: numbers[item[NUMBER_KEY]]} for item in held[sid] if _numbered(item, numbers)
        ]
        for sid in sorted(sentences)
        if sid in held
    }
    authored = {page: number for number, page in numbers.items()}
    shown = sorted({item[NUMBER_KEY] for items in sents.values() for item in items})
    sources = {
        str(page): {**listed[str(authored[page])], NUMBER_KEY: page}
        for page in shown
        if str(authored[page]) in listed
    }
    return {READER_DATA: {SENTENCES_KEY: sents, SOURCES_KEY: sources}}


def unit_sentences(units: Iterable[Iterable[Any]]) -> set[str]:
    return {sid for nodes in units for sid in _node_sentences(nodes)}


def fragment_sentences(markup: str) -> set[str]:
    return set(SENTENCE_ATTRIBUTE.findall(markup))


def merged_data(held: dict[str, Any], found: Mapping[str, Any]) -> None:
    for key, value in found.items():
        known = held.get(key)
        if key == MOLECULE_DATA and isinstance(known, dict) and isinstance(value, Mapping):
            held[key] = {**known, **value}
        elif key == READER_DATA and isinstance(known, dict) and isinstance(value, Mapping):
            held[key] = {
                part: {**known.get(part, {}), **value.get(part, {})} for part in (SENTENCES_KEY, SOURCES_KEY)
            }
        else:
            held.setdefault(key, value)


def _numbered(item: Any, numbers: Mapping[int, int]) -> bool:
    return isinstance(item, Mapping) and item.get(NUMBER_KEY) in numbers


def _node_sentences(nodes: Iterable[Any]) -> list[str]:
    found: list[str] = []
    for node in nodes:
        if isinstance(node, Mapping):
            if isinstance(node.get(SENTENCE_ID_KEY), str):
                found.append(node[SENTENCE_ID_KEY])
            found += _node_sentences(node.get("c", []))
    return found
