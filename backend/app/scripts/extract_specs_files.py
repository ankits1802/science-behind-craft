from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from app.core.errors import InvalidInput
from app.research.base import ContractModel
from app.research.monograph_document import spec_file_name
from app.research.monograph_page import CitedSource, ComponentEntry, MonographContent

from .build_monograph import MONOGRAPHS_DIR, TEMPLATE_FILE, monograph_content
from .extract_specs_markup import Element, find_anchor, parse_markup

__all__ = [
    "ANCHOR_CORRECTIONS",
    "SPECS_FOLDER",
    "Extractor",
    "Found",
    "SpecGroup",
    "extracted_specs",
    "run_group",
    "spec_path",
    "spec_text",
]

SPECS_FOLDER = "specs"
JSON_INDENT = 1
ANCHOR_CORRECTIONS: Mapping[str, str] = MappingProxyType(
    {"kutch-ajrakh/policy/gi-registration-card": '[class="label-card gi"]'}
)


@dataclass(frozen=True)
class Found:
    component: ComponentEntry
    element: Element
    sources: Mapping[str, CitedSource]
    placed: Mapping[int, str] = MappingProxyType({})

    def component_at(self, element: Element) -> str | None:
        label = self.placed.get(id(element))
        return label if label != self.component.label else None

    def held_components(self) -> list[str]:
        return self._held_within(self.element)

    def _held_within(self, element: Element) -> list[str]:
        held: list[str] = []
        for child in element.elements():
            label = self.component_at(child)
            held.extend([label] if label else self._held_within(child))
        return held


Extractor = Callable[[Found], dict[str, Any]]


@dataclass(frozen=True)
class SpecGroup:
    name: str
    models: Mapping[str, type[ContractModel]]
    extractors: Mapping[str, Extractor]


def spec_path(slug: str, label: str) -> Path:
    return MONOGRAPHS_DIR / slug / SPECS_FOLDER / spec_file_name(label)


def spec_text(spec: ContractModel) -> str:
    return (
        json.dumps(spec.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=JSON_INDENT) + "\n"
    )


def component_element(tree: Element, component: ComponentEntry) -> Element:
    return find_anchor(tree, ANCHOR_CORRECTIONS.get(component.label, component.anchor))


def extracted_specs(group: SpecGroup, content: MonographContent, template: str) -> dict[str, ContractModel]:
    tree = parse_markup(template)
    elements = {component.label: component_element(tree, component) for component in content.components}
    placed = MappingProxyType({id(element): label for label, element in elements.items()})
    specs: dict[str, ContractModel] = {}
    for component in content.components:
        extractor = group.extractors.get(component.kind)
        if extractor is None:
            continue
        found = Found(component, elements[component.label], content.sources, placed)
        spec = group.models[component.kind].model_validate(extractor(found))
        _names_what_it_holds(found, spec.model_dump(mode="json"))
        specs[component.label] = spec
    return specs


def _names_what_it_holds(found: Found, spec: Any) -> None:
    held = set(found.held_components())
    named = _strings(spec) & set(found.placed.values())
    if held != named:
        raise InvalidInput(
            f"{found.component.label} holds the components {sorted(held)} but its spec names {sorted(named)}"
        )


def _strings(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        return set().union(set(), *(_strings(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(set(), *(_strings(item) for item in value))
    return set()


def _group_specs(group: SpecGroup, slug: str) -> dict[str, ContractModel]:
    template = (MONOGRAPHS_DIR / slug / TEMPLATE_FILE).read_bytes().decode("utf-8")
    return extracted_specs(group, monograph_content(slug), template)


def stale_specs(group: SpecGroup, slug: str) -> list[str]:
    stale = []
    for label, spec in _group_specs(group, slug).items():
        path = spec_path(slug, label)
        if not path.exists() or path.read_bytes().decode("utf-8") != spec_text(spec):
            stale.append(label)
    return stale


def write_specs(group: SpecGroup, slug: str) -> list[str]:
    specs = _group_specs(group, slug)
    for label, spec in specs.items():
        path = spec_path(slug, label)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(spec_text(spec).encode("utf-8"))
    return sorted(specs)


def run_group(group: SpecGroup, argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(prog=f"extract_specs_{group.name}")
    parser.add_argument("slug", help="the monograph folder, such as Kutch-Ajrakh")
    parser.add_argument("--check", action="store_true", help="report spec files that differ from extraction")
    args = parser.parse_args(argv)
    if args.check:
        stale = stale_specs(group, args.slug)
        print(json.dumps({"ok": not stale, "stale": stale}))
        return 1 if stale else 0
    print(json.dumps({"ok": True, "written": write_specs(group, args.slug)}))
    return 0
