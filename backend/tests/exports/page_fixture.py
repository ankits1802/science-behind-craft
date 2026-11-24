from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cache
from typing import Any

from app.data.kind_fixture_files import KIND_FIXTURE_ORDER, kind_fixtures
from app.research.monograph_document import MonographDocument
from app.research.monograph_page import (
    ChapterName,
    CitedSource,
    ComponentEntry,
    LayoutEntry,
    MonographContent,
    Quote,
    TextUnit,
)
from app.services.kind_fixture_specs import placed_fixture_spec
from app.services.monograph_document import authored_document, monograph_content
from app.services.monograph_generated_units import cited_nodes
from app.services.page_export_document import page_export
from app.services.page_export_model import PageExport

__all__ = [
    "FIXTURE_LABELS",
    "FIXTURE_SLUG",
    "LEDE",
    "NEW_KINDS",
    "fixture_export",
    "fixture_page",
    "fixture_refs",
    "kutch_document",
]

FIXTURE_SLUG = "Every-New-Kind"
LEDE = "u0001"
NEW_KINDS = (
    "timeline_map",
    "diagram_kit",
    "swatch_cards",
    "reaction_player",
    "dip_player",
    "stage_player",
    "molecule_3d",
    "label_card",
    "experiment_lab",
    "choice_toggle",
    "choice_toggle_copper",
)
CHAPTERS = {"HISTORY": "history", "PROCESS": "made", "CHEMISTRY": "chemistry", "POLICY": "market"}
CHAPTER_TITLES = {
    "opening": "Every new kind",
    "history": "History",
    "made": "How it is made",
    "chemistry": "The chemistry",
    "market": "Market and GI",
}
FIXTURE_LABELS = {
    "timeline_map": "bidriware/history/where-bidri-was-made",
    "diagram_kit": "bidriware/process/white-to-black-in-the-bath",
    "swatch_cards": "bidriware/chemistry/colours-of-the-alloy",
    "reaction_player": "bidriware/chemistry/patina-steps",
    "dip_player": "bidriware/chemistry/fort-earth-dip",
    "stage_player": "bastar-dhokra/process/lost-wax-stages",
    "molecule_3d": "bidriware/chemistry/ammonium-chloride",
    "label_card": "bidriware/policy/gi-registration-card",
    "experiment_lab": "bidriware/chemistry/what-if-lab",
    "choice_toggle": "bidriware/chemistry/what-blackens",
    "choice_toggle_copper": "bidriware/chemistry/why-copper",
}


@dataclass
class _Page:
    sources: dict[str, CitedSource] = field(default_factory=dict)
    keys: dict[tuple[str, str], str] = field(default_factory=dict)
    units: dict[str, TextUnit] = field(default_factory=dict)
    citations: dict[str, list[Quote]] = field(default_factory=dict)
    claims: dict[str, list[str]] = field(default_factory=dict)
    components: list[ComponentEntry] = field(default_factory=list)
    layout: list[LayoutEntry] = field(default_factory=list)
    specs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def source_key(self, craft: str, source_id: str, source: Mapping[str, Any]) -> str:
        known = self.keys.get((craft, source_id))
        if known is not None:
            return known
        key = f"g{len(self.sources) + 1}"
        self.keys[(craft, source_id)] = key
        self.sources[key] = CitedSource(
            number=len(self.sources) + 1,
            title=str(source["title"]),
            full_title=None,
            publisher=source.get("publisher"),
            year=source.get("year"),
            grade=source.get("reliability"),
            url=source.get("url"),
            extra=None,
            dossier_source_id=source_id,
        )
        return key


@cache
def fixture_export() -> PageExport:
    page = fixture_page()
    return page_export(page, page.specs)


def kutch_document() -> MonographDocument:
    page_url = "https://kalavigyan.example/crafts/Kutch-Ajrakh"
    return authored_document(monograph_content("Kutch-Ajrakh"), title="Kutch Ajrakh", page_url=page_url)


def fixture_refs(index: int, fixture: Mapping[str, Any]) -> dict[str, str]:
    return {ref: f"u{(index + 1) * 100 + number:04d}" for number, ref in enumerate(fixture["units"], start=1)}


def fixture_page() -> MonographDocument:
    by_name = dict(zip(KIND_FIXTURE_ORDER, kind_fixtures(), strict=True))
    page = _Page()
    lede = TextUnit(
        chapter="opening", tag="p", field="OVERVIEW", nodes=["One page draws every new kind."], claim_ids=[]
    )
    page.units[LEDE] = lede
    page.layout.append(LayoutEntry(chapter="opening", kind="unit", ref=LEDE))
    for index, name in enumerate(NEW_KINDS):
        _add(page, by_name[name], fixture_refs(index, by_name[name]))
    order = list(dict.fromkeys(entry.chapter for entry in page.layout))
    content = MonographContent(
        craft_slug=FIXTURE_SLUG,
        sources=page.sources,
        citations=page.citations,
        citation_claims=page.claims,
        data={},
        units=page.units,
        components=page.components,
        layout=page.layout,
        chapters=[ChapterName(key=key, title=CHAPTER_TITLES[key], rail=CHAPTER_TITLES[key]) for key in order],
    )
    return MonographDocument(
        subject_kind="craft",
        subject_slug=FIXTURE_SLUG,
        title="Every new kind",
        version=1,
        content=content,
        specs=page.specs,
        page_url=f"https://kalavigyan.example/crafts/{FIXTURE_SLUG}",
    )


def _add(page: _Page, fixture: Mapping[str, Any], refs: Mapping[str, str]) -> None:
    label = str(fixture["label"])
    chapter = CHAPTERS[str(fixture["field"])]
    page.components.append(
        ComponentEntry(
            label=label,
            chapter=chapter,
            anchor=f"#{label.rsplit('/', 1)[-1]}",
            kind=fixture["kind"],
            title=fixture["title"],
            description=fixture["description"],
            field=fixture["field"],
            fields=[],
            subjects=[],
        )
    )
    page.layout.append(LayoutEntry(chapter=chapter, kind="component", ref=label, within=fixture["within"]))
    page.specs[label] = _renamed(placed_fixture_spec(fixture["spec"], fixture.get("placed")), refs)
    for ref, unit in fixture["units"].items():
        _unit(page, fixture, (refs[ref], chapter), unit)
        page.layout.append(LayoutEntry(chapter=chapter, kind="unit", ref=refs[ref], within=label))


def _unit(page: _Page, fixture: Mapping[str, Any], placed: tuple[str, str], unit: Mapping[str, Any]) -> None:
    ref, chapter = placed
    craft = str(fixture["craft"])
    quotes: list[Quote] = []
    for claim in unit["claims"]:
        for quote in fixture["facts"][claim]["quotes"]:
            key = page.source_key(craft, quote["source"], fixture["sources"][quote["source"]])
            shown = Quote(source=key, locator=quote.get("locator"), quote=quote.get("quote"))
            if shown not in quotes:
                quotes.append(shown)
    keys = list(dict.fromkeys(quote.source for quote in quotes))
    nodes = cited_nodes(str(unit["text"]), ref, keys)
    page.units[ref] = TextUnit(
        chapter=chapter, tag="p", field=fixture["field"], nodes=nodes, claim_ids=list(unit["claims"])
    )
    if quotes:
        page.citations[ref] = quotes
        page.claims[ref] = list(unit["claims"])


def _renamed(value: Any, refs: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        return refs.get(value, value)
    if isinstance(value, Mapping):
        return {key: _renamed(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_renamed(item, refs) for item in value]
    return value
