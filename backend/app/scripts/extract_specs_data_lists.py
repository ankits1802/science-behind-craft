from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.core.errors import InvalidInput

from .extract_specs_files import Extractor, Found
from .extract_specs_markup import Element, has_classes, is_tag
from .extract_specs_parts import child_with, held_text, slot_unit, text_line, url_reference

__all__ = ["LIST_EXTRACTORS", "concept_meta", "more_label"]

CONCEPT_META = re.compile(r"(?P<place>.+?) · (?P<family>.+) · named in (?P<sentences>\d+) cited sentences?")
CRAFT_FOOT = re.compile(r"(?P<place>.+) · (?P<sources>\d+) sources")
SUPPORTS = re.compile(r"Supports (?P<sentences>\d+) sentences? here")
TILE = "tile-{}"


def concept_meta(place: str, family: str, sentences: int) -> str:
    return f"{place} · {family} · named in {sentences} cited sentence{'' if sentences == 1 else 's'}"


def more_label(count: int) -> str:
    return f"Show all {count}"


def concept_atlas(found: Found) -> dict[str, Any]:
    atlas = found.element
    return {
        "title": slot_unit(atlas.first(has_classes("kv-sub-h"))),
        "description": slot_unit(atlas.first(has_classes("kv-sub-d"))),
        "groups": [_concept_group(group, found) for group in atlas.all(has_classes("res-group"))],
    }


def _concept_group(group: Element, found: Found) -> dict[str, Any]:
    concept = child_with(group, "res-concept") or group
    told = concept.elements()
    first = [_concept_row(row, found) for row in (child_with(group, "res-list") or group).elements()]
    details = [part for part in group.elements() if part.name == "details"]
    more = [_concept_row(row, found) for row in details[0].first(is_tag("ol")).elements()] if details else []
    if details and details[0].first(has_classes("kv-more-o")).text() != more_label(len(first) + len(more)):
        raise InvalidInput(f"The concept group {group.attrs['id']} counts other rows than it shows")
    return {
        "id": group.attrs["id"],
        "title": slot_unit(told[0]),
        "text": slot_unit(told[1]),
        "together": slot_unit(told[2]),
        "first": first,
        "more": more,
    }


def _concept_row(row: Element, found: Found) -> dict[str, Any]:
    meta = row.first(has_classes("res-meta")).text()
    said = CONCEPT_META.fullmatch(meta)
    if said is None or concept_meta(said["place"], said["family"], int(said["sentences"])) != meta:
        raise InvalidInput(f"The concept row {meta!r} does not say where and how often the craft is named")
    return {
        "name": row.first(has_classes("res-name")).text(),
        "place": said["place"],
        "family": said["family"],
        "sentences": int(said["sentences"]),
        "sentence": text_line(row.first(has_classes("res-s")), found.sources),
    }


def related_crafts(found: Found) -> dict[str, Any]:
    block = found.element.first(has_classes("end-block"))
    head = block.first(has_classes("end-h"))
    cards = block.all(has_classes("rel-card"))
    return {
        "title": slot_unit(head.first(is_tag("h3"))),
        "kicker": head.first(has_classes("kicker")).text(),
        "description": slot_unit(block.first(has_classes("end-dek"))),
        "weave": url_reference(cards[0].all(is_tag("rect"))[1].attrs["fill"]),
        "crafts": [_related_craft(card, found) for card in cards],
    }


def _related_craft(card: Element, found: Found) -> dict[str, Any]:
    plate = card.first(has_classes("tplate"))
    tile = int(plate.attrs["data-tile"])
    if url_reference(plate.first(is_tag("rect")).attrs["fill"]) != TILE.format(tile):
        raise InvalidInput(f"The related craft's plate is not drawn on tile {tile}")
    foot = CRAFT_FOOT.fullmatch(plate.first(has_classes("tp-foot")).elements()[0].text())
    if foot is None:
        raise InvalidInput("A related craft's plate names its place and its sources")
    tags = plate.all(has_classes("tag"))
    share = card.first(has_classes("rel-share"))
    return {
        "tile": tile,
        "swatch": held_text(plate.first(has_classes("kv-sw-l")), found.sources),
        "top": plate.first(has_classes("tp-top")).text(),
        "name": plate.first(has_classes("native")).text(),
        "place": foot["place"],
        "sources": int(foot["sources"]),
        "monograph": any(tag.has_class("mono") for tag in tags),
        "gi": any(tag.text().startswith("GI") for tag in tags),
        "shares": held_text(share.first(has_classes("k")), found.sources),
        "sentence": slot_unit(share.first(is_tag("p"))),
    }


def source_list(found: Found) -> dict[str, Any]:
    element = found.element
    if element.attrs.get("role") == "status":
        return {"setting": "status", "statusId": element.attrs["id"]}
    listing = {
        "id": element.attrs["id"],
        "title": slot_unit(element.first(has_classes("kv-sub-h"))),
        "description": slot_unit(element.first(has_classes("kv-sub-d"))),
        "openLabel": element.first(has_classes("kv-more-o")).text(),
        "closeLabel": element.first(has_classes("kv-more-c")).text(),
        "sources": [_listed_source(item, found) for item in element.all(is_tag("li"))],
    }
    return {"setting": "listing", "listing": listing}


def _listed_source(item: Element, found: Found) -> dict[str, Any]:
    button = item.first(is_tag("button"))
    key = button.attrs["data-g"]
    told = item.first(is_tag("small")).elements()
    supports = SUPPORTS.fullmatch(told[2].text())
    link = item.first(is_tag("a"))
    margin = item.all(has_classes("mg"))
    number = int(button.first(is_tag("b")).text())
    if (
        supports is None
        or found.sources[key].number != number
        or found.sources[key].url != link.attrs["href"]
    ):
        raise InvalidInput(f"The listed source {key} differs from the page's source table")
    return {
        "key": key,
        "number": number,
        "title": item.first(has_classes("src-t")).text(),
        "meta": told[0].text(),
        "grade": next(cls for cls in told[1].first(has_classes("rel")).classes if cls != "rel"),
        "gradeLabel": told[1].text(),
        "sentences": int(supports["sentences"]),
        "margin": margin[0].text() if margin else None,
        "url": link.attrs["href"],
        "linkLabel": link.first(has_classes("vh")).text(),
    }


def source_disagreements(found: Found) -> dict[str, Any]:
    section = found.element
    heading = section.first(is_tag("h3"))
    return {
        "id": section.attrs["id"],
        "titleId": heading.attrs["id"],
        "title": heading.text().strip(),
        "intro": slot_unit(section.first(has_classes("sec-intro"))),
        "items": [
            _disagreement(item, found) for item in section.first(has_classes("differ-list")).elements()
        ],
    }


def _disagreement(item: Element, found: Found) -> dict[str, Any]:
    details = item.first(is_tag("details"))
    if "open" not in details.attrs:
        raise InvalidInput("Every disagreement is shown open")
    readings = details.all(has_classes("reading"))
    figures = details.all(has_classes("rangefig"))
    return {
        "summary": held_text(details.first(is_tag("summary")).elements()[0], found.sources),
        "readings": [
            {"who": reading.first(has_classes("who")).text(), "unit": slot_unit(reading.first(is_tag("p")))}
            for reading in readings
        ],
        "figure": _range_figure(figures[0], found) if figures else None,
    }


def _range_figure(figure: Element, found: Found) -> dict[str, Any]:
    number = figure.first(has_classes("fig-no"))
    chart = found.component_at(figure.first(is_tag("svg")))
    if chart is None:
        raise InvalidInput("A disagreement's figure draws a chart component")
    return {
        "number": {"unit": slot_unit(number), "ref": number.attrs["data-fig"]},
        "title": slot_unit(figure.first(has_classes("chart-title"))),
        "dek": slot_unit(figure.first(has_classes("chart-dek"))),
        "chart": chart,
        "source": slot_unit(figure.first(has_classes("src-line"))),
    }


def citation_tool(found: Found) -> dict[str, Any]:
    section = found.element
    heading = section.first(is_tag("h3"))
    tabs = section.first(lambda part: part.attrs.get("role") == "tablist")
    panels = [part for part in section.elements() if part.has_class("kv-cp")]
    return {
        "title": slot_unit(heading),
        "titleId": heading.attrs["id"],
        "tabsLabel": tabs.attrs["aria-label"],
        "panels": [_cite_panel(tab, panel) for tab, panel in zip(tabs.elements(), panels, strict=True)],
    }


def _cite_panel(tab: Element, panel: Element) -> dict[str, Any]:
    box = panel.elements()[0]
    screen = box.elements()[0]
    cites = screen.elements()[0]
    cite_box = cites.elements()[0]
    buttons = cite_box.first(has_classes("seg")).elements()
    key = "style" if "data-style" in buttons[0].attrs else "cite-style"
    text = cite_box.first(has_classes("cb-text"))
    copy = cite_box.first(lambda part: "data-copy" in part.attrs)
    styles = [button.attrs[f"data-{key}"] for button in buttons]
    return {
        "key": tab.attrs["data-kv-ct"],
        "tabId": tab.attrs["id"],
        "panelId": panel.attrs["id"],
        "label": tab.text(),
        "box": box.classes,
        "aid": screen.attrs["data-aid"],
        "cites": cites.classes,
        "boxId": cite_box.attrs.get("id"),
        "styleKey": key,
        "styles": [
            {"value": value, "label": button.text(), "text": text.attrs[f"data-{value}"]}
            for value, button in zip(styles, buttons, strict=True)
        ],
        "textId": text.attrs["id"],
        "text": slot_unit(text),
        "link": slot_unit(cite_box.first(has_classes("cb-link"))),
        "copyLabel": copy.text(),
    }


LIST_EXTRACTORS: Mapping[str, Extractor] = {
    "concept_atlas": concept_atlas,
    "related_crafts": related_crafts,
    "source_list": source_list,
    "source_disagreements": source_disagreements,
    "citation_tool": citation_tool,
}
