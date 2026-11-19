import argparse
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from app.core.errors import InvalidInput
from app.research.base import ContractModel
from app.research.component_specs_science import SPEC_MODELS_SCIENCE
from app.research.monograph_document import spec_file_name
from app.research.monograph_page import ComponentEntry

from .build_monograph import MONOGRAPHS_DIR, TEMPLATE_FILE, monograph_content
from .extract_specs_science_dom import Element, anchored, find_anchor, parse_fragment
from .extract_specs_science_explainers import material_cards, model_explainer, process_replay
from .extract_specs_science_figures import diagram, equation_card, molecule_3d, structure_diagram
from .extract_specs_science_players import dip_player, reaction_player
from .extract_specs_science_stages import stage_player

SPECS_FOLDER = "specs"
SLUGS = ("Kutch-Ajrakh",)
CITATION_CLASS = "kcite"

Extractor = Callable[[Element, Mapping[int, str]], dict[str, Any]]


def _plain(read: Callable[[Element], dict[str, Any]]) -> Extractor:
    return lambda element, _nested: read(element)


EXTRACTORS: Mapping[str, Extractor] = MappingProxyType(
    {
        "diagram": _plain(diagram),
        "dip_player": _plain(dip_player),
        "equation_card": _plain(equation_card),
        "material_cards": material_cards,
        "model_explainer": _plain(model_explainer),
        "molecule_3d": _plain(molecule_3d),
        "process_replay": _plain(process_replay),
        "reaction_player": _plain(reaction_player),
        "stage_player": _plain(stage_player),
        "structure_diagram": _plain(structure_diagram),
    }
)


@dataclass(frozen=True)
class HeldCitation:
    label: str
    citation: str


@dataclass(frozen=True)
class Extraction:
    specs: Mapping[str, ContractModel]
    held: tuple[HeldCitation, ...]


def extract_specs(slug: str) -> Extraction:
    template = (MONOGRAPHS_DIR / slug / TEMPLATE_FILE).read_bytes().decode("utf-8")
    root = parse_fragment(template)
    content = monograph_content(slug)
    labels = _placed_components(root, content.components)
    specs: dict[str, ContractModel] = {}
    held: list[HeldCitation] = []
    for component in content.components:
        extractor = EXTRACTORS.get(component.kind)
        if extractor is None:
            continue
        element = find_anchor(root, component.anchor)
        nested = {key: label for key, label in labels.items() if key != id(element)}
        specs[component.label] = SPEC_MODELS_SCIENCE[component.kind].model_validate(
            extractor(element, nested)
        )
        held += [HeldCitation(component.label, key) for key in held_citations(element, nested)]
    return Extraction(specs, tuple(held))


def _placed_components(root: Element, components: Sequence[ComponentEntry]) -> dict[int, str]:
    placed: dict[int, str] = {}
    for component in components:
        found = anchored(root, component.anchor)
        if len(found) > 1:
            raise InvalidInput(
                f"anchor {component.anchor} of {component.label} matches {len(found)} elements"
            )
        placed |= {id(element): component.label for element in found}
    return placed


def held_citations(element: Element, nested: Mapping[int, str]) -> list[str]:
    found: list[str] = []

    def walk(node: Element) -> None:
        if id(node) in nested:
            return
        if node.tag == "button" and node.has_class(CITATION_CLASS):
            found.append(node.attrs["data-c"])
        for child in node.elements:
            walk(child)

    walk(element)
    return found


def spec_text(spec: ContractModel) -> str:
    return json.dumps(spec.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=1) + "\n"


def specs_dir(slug: str) -> Path:
    return MONOGRAPHS_DIR / slug / SPECS_FOLDER


def write_specs(slug: str) -> Extraction:
    extraction = extract_specs(slug)
    folder = specs_dir(slug)
    folder.mkdir(exist_ok=True)
    for label, spec in extraction.specs.items():
        (folder / spec_file_name(label)).write_bytes(spec_text(spec).encode("utf-8"))
    return extraction


def stale_specs(slug: str) -> list[str]:
    folder = specs_dir(slug)
    return [
        label
        for label, spec in extract_specs(slug).specs.items()
        if not (folder / spec_file_name(label)).is_file()
        or (folder / spec_file_name(label)).read_bytes().decode("utf-8") != spec_text(spec)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="extract_specs_science")
    parser.add_argument("--check", action="store_true", help="report spec files that differ from extraction")
    args = parser.parse_args(argv)
    if args.check:
        stale = {slug: stale_specs(slug) for slug in SLUGS}
        print(json.dumps({"ok": not any(stale.values()), "stale": stale}))
        return 1 if any(stale.values()) else 0
    written = {slug: write_specs(slug) for slug in SLUGS}
    report = {
        slug: {"specs": len(extraction.specs), "held": [vars(item) for item in extraction.held]}
        for slug, extraction in written.items()
    }
    print(json.dumps({"ok": True, "written": report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
