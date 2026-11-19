from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.core.errors import InvalidInput

from .extract_specs_science_dom import Element
from .extract_specs_science_read import drawing, expect, kids, one_of, only, rich, slot, text_of, unit_of

__all__ = ["material_cards", "model_explainer", "process_replay"]

SWATCH_STYLE = re.compile(r"background:var\((--[a-z0-9-]+)\)")
HEIGHT_STYLE = re.compile(r"height:(\d+)px")
ORDER_STYLE = "--i:{index}"


def material_cards(element: Element, nested: Mapping[int, str]) -> dict[str, Any]:
    spread, cards, *after = kids(expect(element, "section", "sec"))
    heading, intro = kids(expect(only(expect(spread, "div", "spread")), "div", "main"))
    expect(heading, "h3", "sec-h")
    expect(heading.children[0], "span", "sw", "sw-mat")
    return {
        "id": element.attrs["id"],
        "headingId": heading.attrs["id"],
        "heading": "".join(str(part) for part in heading.children[1:]),
        "intro": unit_of(expect(intro, "p", "sec-intro", "t-body")),
        "cards": [_material(card) for card in kids(expect(cards, "div", "mats"))],
        "after": [slot(part, nested) for part in after],
    }


def model_explainer(element: Element) -> dict[str, Any]:
    caption, box = kids(expect(element, "figure", "model-frame"))
    number, title = kids(expect(caption, "figcaption", "mf-cap"))
    stylesheet, *stills, frame = kids(expect(box, "div", "model-box"))
    read = [_still(still) for still in stills]
    shared = [{key: value for key, value in still.items() if key != "still"} for still in read]
    if any(found != shared[0] for found in shared):
        raise InvalidInput("the stills of a model explainer share their badge, controls and key")
    return {
        "head": {
            "figure": expect(number, "p", "fig-no").attrs.get("data-fig"),
            "number": unit_of(number),
            "title": unit_of(expect(title, "p", "mf-t")),
            "titleId": title.attrs["id"],
            "dek": None,
        },
        **shared[0],
        "stills": [still["still"] for still in read],
        "model": _model_document(stylesheet, frame),
    }


def process_replay(element: Element) -> dict[str, Any]:
    top, understood, progress, grid, ready = kids(expect(element, "div", "kv-made-how"))
    first, angles = kids(expect(understood, "div", "understood", "kv-understood"))
    stages, _status = kids(expect(progress, "nav", "prog"))
    sources, sections = kids(expect(grid, "div", "kv-made-grid"))
    sources_kicker, source_list = kids(expect(sources, "div", "kv-made-col"))
    sections_kicker, section_list = kids(expect(sections, "div", "kv-made-col"))
    return {
        "play": text_of(expect(only(expect(top, "div", "kv-made-top")), "button", "btn", "sm")),
        "understood": unit_of(expect(first, "p")),
        "angles": unit_of(expect(angles, "p", "u-a")),
        "stages": [_stage(stage) for stage in kids(expect(stages, "ol"))],
        "sourcesKicker": unit_of(expect(sources_kicker, "p", "kicker")),
        "sources": [
            _source(index, item) for index, item in enumerate(kids(expect(source_list, "ol", "kv-made-src")))
        ],
        "sectionsKicker": unit_of(expect(sections_kicker, "p", "kicker")),
        "sections": [
            _section(index, item)
            for index, item in enumerate(kids(expect(section_list, "ol", "kv-made-sec")))
        ],
        "ready": unit_of(expect(ready, "p", "kv-made-ready")),
    }


def _material(card: Element) -> dict[str, Any]:
    swatch, role, name, local, *rest = kids(expect(card, "div", "mat"))
    *botanical, chemistry, facts = rest
    crystal = swatch.has_class("crys")
    expect(swatch, "span", *(["msw", "crys"] if crystal else ["msw"]))
    return {
        "swatch": "crystal" if crystal else _style(SWATCH_STYLE, swatch),
        "role": unit_of(expect(role, "p", "mk2")),
        "name": unit_of(expect(name, "h4")),
        "local": unit_of(expect(local, "p", "loc")),
        "botanical": unit_of(expect(botanical[0], "p", "bot")) if botanical else None,
        "chemistry": unit_of(expect(chemistry, "p", "chem")),
        "facts": [unit_of(expect(fact, "p")) for fact in kids(expect(facts, "div", "facts"))],
    }


def _still(still: Element) -> dict[str, Any]:
    width = [name for name in still.classes if name != "model-still"]
    frame = only(expect(still, "div", "model-still", *width))
    badge, heading, lede, stage, controls, numbers, key = kids(expect(frame, "div", "kx"))
    badge_name, badge_note = kids(expect(badge, "div", "mb"))
    picture, phase = kids(expect(stage, "div", "kx-st"))
    return {
        "badge": text_of(expect(badge_name, "span", "mb-k")),
        "badgeNote": text_of(expect(badge_note, "span", "mb-d")),
        "controls": _controls(controls),
        "key": [_key_item(item) for item in kids(expect(key, "div", "kx-k"))],
        "still": {
            "width": width[0],
            "heading": unit_of(expect(heading, "h2", "kx-h")),
            "lede": unit_of(expect(lede, "p", "kx-l")),
            "drawing": drawing(picture),
            "phase": unit_of(expect(phase, "p", "kx-ph")),
            "numbers": unit_of(expect(numbers, "p", "kx-n")),
        },
    }


def _controls(controls: Element) -> dict[str, Any]:
    button, slider = kids(expect(controls, "div", "kx-c"))
    icon, play = kids(expect(button, "button", "kx-b"))
    label, track, ticks = kids(expect(slider, "div", "kx-s"))
    expect(track, "input")
    return {
        "play": text_of(expect(play, "span")),
        "playIcon": drawing(icon),
        "sliderLabel": text_of(expect(label, "label", "vh")),
        "sliderMax": int(track.attrs["max"]),
        "sliderAt": int(track.attrs["value"]),
        "ticks": [text_of(tick) for tick in kids(expect(ticks, "div", "kx-tk"))],
    }


def _key_item(item: Element) -> dict[str, Any]:
    icon, *label = item.children
    if not isinstance(icon, Element) or not all(isinstance(part, str) for part in label):
        raise InvalidInput("a key item is an icon and its words")
    return {"style": item.attrs.get("class"), "icon": drawing(icon), "label": "".join(map(str, label))}


def _model_document(stylesheet: Element, frame: Element) -> dict[str, Any]:
    expect(stylesheet, "style")
    expect(frame, "iframe", "kv-frame")
    if frame.attrs["sandbox"] != "allow-scripts":
        raise InvalidInput("a model-built document runs sandboxed with scripts only")
    return {
        "title": frame.attrs["title"],
        "height": int(_style(HEIGHT_STYLE, frame)),
        "stylesheet": stylesheet.text(),
        "document": frame.attrs["data-srcdoc"],
        "sandbox": "allow-scripts",
    }


def _stage(stage: Element) -> dict[str, Any]:
    tick, label, detail, state = kids(expect(stage, "li", "is-done"))
    expect(tick, "span", "pg-ok")
    expect(state, "span", "vh", "pg-state")
    return {
        "label": text_of(expect(label, "span", "pg-l")),
        "detail": text_of(expect(detail, "span", "pg-d")),
        "startMs": int(stage.attrs["data-kv-a"]),
        "endMs": int(stage.attrs["data-kv-b"]),
    }


def _source(index: int, item: Element) -> dict[str, Any]:
    number, title, grade = kids(_ordered(index, expect(item, "li", "kv-ms")))
    if text_of(expect(number, "b")) != str(index + 1):
        raise InvalidInput(f"source row {index} is not numbered {index + 1}")
    mark = one_of(expect(grade, "span", "relw").elements)
    letter = text_of_after(grade, mark)
    expect(mark, "span", "rel", letter)
    return {"title": text_of(expect(title, "span", "kv-ms-t")), "grade": letter}


def _section(index: int, item: Element) -> dict[str, Any]:
    number, title, made = kids(_ordered(index, expect(item, "li", "kv-mw")))
    tick, words = kids(expect(made, "span", "kv-mw-f"))
    expect(tick, "span", "kv-ok")
    if text_of(expect(number, "b")) != str(index + 1):
        raise InvalidInput(f"section row {index} is not numbered {index + 1}")
    return {"title": text_of(expect(title, "span", "kv-mw-t")), "made": rich(expect(words, "span").children)}


def _ordered(index: int, item: Element) -> Element:
    if item.attrs.get("style") != ORDER_STYLE.format(index=index):
        raise InvalidInput(f"row {index} carries {item.attrs.get('style')!r} for its order")
    return item


def text_of_after(parent: Element, mark: Element) -> str:
    rest = parent.children[parent.children.index(mark) + 1 :]
    return "".join(str(part) for part in rest)


def _style(pattern: re.Pattern[str], element: Element) -> str:
    found = pattern.fullmatch(element.attrs.get("style", ""))
    if found is None:
        raise InvalidInput(
            f"<{element.tag}> style {element.attrs.get('style')!r} does not read as {pattern.pattern}"
        )
    return found.group(1)
