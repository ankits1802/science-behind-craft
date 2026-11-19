from __future__ import annotations

import json
import re
from typing import Any

from app.core.errors import InvalidInput
from app.research.component_specs_data import SPEC_MODELS_DATA

from .extract_specs_data_lists import LIST_EXTRACTORS
from .extract_specs_data_maps import MAP_EXTRACTORS
from .extract_specs_files import Found, SpecGroup, run_group
from .extract_specs_markup import Element, has_classes, is_tag
from .extract_specs_parts import drawing, figure_head, placed, slot_unit, style_of, text_line

__all__ = ["DATA", "bar_share", "main"]

SHOWN_NUMBER = re.compile(r"[\d,]+(\.\d+)?")
SHARE_DIGITS = 2
SMALL_BAR_WIDTH = "2px"


def bar_share(value: float, largest: float) -> str:
    share = round(value / largest * 100, SHARE_DIGITS)
    return f"{share:g}%"


def chart(found: Found) -> dict[str, Any]:
    element = found.element
    if element.name == "svg":
        return {"form": "drawing", "drawing": drawing(element)}
    if element.name == "div":
        return {"form": "dots", "dots": _dots(element)}
    if element.all(has_classes("yard-row")):
        return {"form": "rows", "rows": _rows(element)}
    if element.all(lambda part: "data-series" in part.attrs):
        return {"form": "series", "series": _series(element, found)}
    source = element.first(has_classes("src-line"))
    figure = {
        "classes": element.classes,
        "head": figure_head(element),
        "drawing": drawing(element.first(is_tag("svg"))),
        "source": text_line(source, found.sources),
    }
    return {"form": "figure", "figure": figure}


def _dots(element: Element) -> dict[str, Any]:
    marks = [dot.has_class("on") for dot in element.elements()]
    if marks != sorted(marks, reverse=True):
        raise InvalidInput("A dot chart marks its first dots")
    return {
        "classes": element.classes,
        "label": element.attrs["aria-label"],
        "total": len(marks),
        "marked": sum(marks),
    }


def _rows(figure: Element) -> dict[str, Any]:
    rows = []
    for row in figure.all(has_classes("yard-row")):
        label, bar, shown = row.elements()
        number = SHOWN_NUMBER.search(shown.text())
        if number is None:
            raise InvalidInput(f"The bar {label.text()!r} shows no number")
        rows.append(
            {
                "label": label.text(),
                "value": float(number.group().replace(",", "")),
                "shown": shown.text(),
                "emphasis": bar.has_class("emph"),
                "bar": bar,
            }
        )
    largest = max(row["value"] for row in rows)
    for row in rows:
        expected = {"width": bar_share(row["value"], largest)}
        if row["value"] < largest:
            expected["min-width"] = SMALL_BAR_WIDTH
        if style_of(row.pop("bar")) != expected:
            raise InvalidInput(f"The bar {row['label']!r} is not drawn to its share of the largest")
    source = figure.first(has_classes("src-line"))
    return {"classes": figure.classes, "head": figure_head(figure), "rows": rows, "source": slot_unit(source)}


def _series(figure: Element, found: Found) -> dict[str, Any]:
    plot = figure.first(lambda part: "data-series" in part.attrs)
    labels = [placed(part, found.sources) for part in plot.elements() if part.name == "span"]
    table = figure.first(is_tag("details"))
    link = figure.first(has_classes("actions")).first(is_tag("a"))
    return {
        "classes": figure.classes,
        "head": figure_head(figure),
        "plot": {
            "classes": plot.classes,
            "label": plot.attrs["aria-label"],
            "comp": plot.attrs["data-comp"],
            "series": json.loads(plot.attrs["data-series"]),
            "drawing": drawing(plot.first(is_tag("svg"))),
            "labels": labels,
        },
        "events": [slot_unit(item) for item in figure.first(is_tag("ol")).elements()],
        "table": _table(table),
        "download": {"href": link.attrs["href"], "fileName": link.attrs["download"], "label": link.text()},
        "source": slot_unit(figure.first(has_classes("src-line"))),
    }


def _table(details: Element) -> dict[str, Any]:
    table = details.first(is_tag("table"))
    rows = [row.elements() for row in table.first(is_tag("tbody")).elements()]
    return {
        "summary": details.first(is_tag("summary")).text(),
        "caption": table.first(is_tag("caption")).text(),
        "head": [slot_unit(cell) for cell in table.first(is_tag("thead")).first(is_tag("tr")).elements()],
        "rows": [
            {
                "head": slot_unit(row[0]),
                "cells": [slot_unit(cell) if cell.children else None for cell in row[1:]],
            }
            for row in rows
        ],
    }


def stat_tiles(found: Found) -> dict[str, Any]:
    tiles = []
    for tile in found.element.elements():
        stat = tile.first(has_classes("t-stat"))
        small = stat.all(is_tag("small"))
        figure = "".join(child for child in stat.children if isinstance(child, str)).strip()
        tiles.append(
            {
                "figure": figure,
                "small": small[0].text() if small else None,
                "caption": slot_unit(tile.first(is_tag("p"))),
            }
        )
    return {"classes": [cls for cls in found.element.classes if cls != "ws-stats"], "tiles": tiles}


def fact_table(found: Found) -> dict[str, Any]:
    section = found.element
    title = section.first(is_tag("h2"))
    rows = section.first(is_tag("dl")).elements()
    return {
        "id": section.attrs["id"],
        "numeral": int(section.first(has_classes("numeral")).text()),
        "chapterNo": slot_unit(section.first(has_classes("chapter-no"))),
        "title": slot_unit(title),
        "titleId": title.attrs["id"],
        "rows": [
            {"term": slot_unit(row.first(is_tag("dt"))), "value": slot_unit(row.first(is_tag("dd")))}
            for row in rows
        ],
    }


def timeline(found: Found) -> dict[str, Any]:
    ladder = found.element
    variant = ladder.classes[0].removesuffix("-ladder")
    scale = ladder.first(has_classes(f"{variant}-scale"))
    number = ladder.first(has_classes("fig-no"))
    return {
        "variant": variant,
        "number": {"unit": slot_unit(number), "ref": number.attrs["data-fig"]},
        "title": slot_unit(ladder.first(has_classes("chart-title"))),
        "scale": {
            "label": scale.attrs["aria-label"],
            "marks": [
                {"left": style_of(mark)["left"], "final": mark.has_class("fin")}
                for mark in scale.all(has_classes("gd"))
            ],
            "spans": [
                {"left": style_of(span)["left"], "text": span.text()}
                for span in scale.all(has_classes("gspan"))
            ],
            "ticks": [
                {
                    "left": style_of(tick)["left"],
                    "side": " ".join(cls for cls in tick.classes if cls != "gx"),
                    "text": tick.text(),
                }
                for tick in scale.all(has_classes("gx"))
            ],
        },
        "steps": [slot_unit(step) for step in ladder.first(is_tag("ol")).elements()],
    }


DATA = SpecGroup(
    name="data",
    models=SPEC_MODELS_DATA,
    extractors={
        "chart": chart,
        "stat_tiles": stat_tiles,
        "fact_table": fact_table,
        "timeline": timeline,
        **MAP_EXTRACTORS,
        **LIST_EXTRACTORS,
    },
)


def main(argv: list[str] | None = None) -> int:
    return run_group(DATA, argv)


if __name__ == "__main__":
    raise SystemExit(main())
