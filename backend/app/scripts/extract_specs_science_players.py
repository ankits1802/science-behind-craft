from __future__ import annotations

import re
from typing import Any

from app.core.errors import InvalidInput

from .extract_specs_science_chem import equation, figure_head
from .extract_specs_science_dom import Element
from .extract_specs_science_read import drawing, expect, kids, one_of, rich, text_of, unit_of

__all__ = ["dip_player", "reaction_player"]

SWATCH_STYLE = re.compile(r"background:var\((--[a-z0-9-]+)\)")
SWATCH_MIX = re.compile(
    r"background:color-mix\(in srgb, var\((--[a-z0-9-]+)\) (\d+)%, var\((--[a-z0-9-]+)\)\)"
)
SWATCH_MARKS = ("clear", "gas", "ion")
PUBCHEM_LINK = re.compile(r"https://pubchem\.ncbi\.nlm\.nih\.gov/compound/(\d+)")


def reaction_player(element: Element) -> dict[str, Any]:
    reacting = element.has_class("rx-player")
    expect(element, "figure", *(["rp", "rx-player"] if reacting else ["rp"]))
    caption, bar, body, chemistry = kids(element)
    rail, _play = kids(expect(bar, "div", "rp-bar"))
    names = [_rail_name(button) for button in kids(expect(rail, "div", "rp-rail"))]
    scene, texts = kids(expect(body, "div", "rp-body"))
    drawn = _reaction_scene(scene) if reacting else _whole_scene(scene, len(names))
    sections = kids(expect(texts, "div", "rp-text"))
    boxes = kids(expect(chemistry, "div", "rp-chems"))
    if not len(names) == len(sections) == len(boxes) == int(element.attrs["data-steps"]):
        raise InvalidInput(f"player {element.attrs['id']} has as many steps as its rail")
    steps = [
        {"name": name, "text": _step_text(section), "chemistry": _chemistry(box), "scene": step_scene}
        for name, section, box, step_scene in zip(names, sections, boxes, drawn["steps"], strict=True)
    ]
    return {
        "id": element.attrs["id"],
        "track": element.attrs["data-track"],
        "head": figure_head(kids(expect(caption, "figcaption", "rp-cap"))),
        "current": int(element.attrs["data-step"]),
        "steps": steps,
        "scenes": drawn["scenes"],
        "key": drawn["key"],
        "status": drawn["status"],
    }


def dip_player(element: Element) -> dict[str, Any]:
    head, scene, strip, controls, formula = kids(expect(element, "figure", "vat"))
    phase, picture = kids(expect(scene, "div", "vat-scene"))
    again, status, dips = kids(expect(controls, "div", "vat-ctl"))
    dips_label, colours = kids(expect(dips, "div", "dips"))
    phases = [_dip_phase(item) for item in kids(expect(strip, "ol", "vat-strip"))]
    swatches = [_dip_swatch(index, item) for index, item in enumerate(kids(expect(colours, "ol")))]
    if element.attrs["data-dips"] != str(len(swatches)) or element.attrs["data-pose"] != phases[-1]["pose"]:
        raise InvalidInput("a dip player rests after its last dip, in its last pose")
    return {
        "id": element.attrs["id"],
        "head": figure_head(kids(expect(head, "figcaption", "vat-head"))),
        "phase": unit_of(expect(phase, "p", "vat-phase")),
        "scene": drawing(expect(picture, "svg", "vat-svg")),
        "stripLabel": strip.attrs["aria-label"],
        "phases": phases,
        "dipAgain": text_of(expect(again, "button", "btn", "vat-dip")),
        "status": unit_of(expect(status, "p", "vat-status")),
        "dipsLabel": unit_of(expect(dips_label, "p", "dips-l")),
        "dips": swatches,
        "equation": equation(formula),
    }


def _rail_name(button: Element) -> str:
    number, name = kids(expect(button, "button"))
    expect(number, "b")
    return text_of(expect(name, "span"))


def _whole_scene(scene: Element, steps: int) -> dict[str, Any]:
    *pictures, status = kids(expect(scene, "div", "rp-scene"))
    return {
        "scenes": [drawing(picture) for picture in pictures],
        "steps": [None] * steps,
        "key": None,
        "status": unit_of(expect(status, "p", "rp-status")),
    }


def _reaction_scene(scene: Element) -> dict[str, Any]:
    *reactions, key, status = kids(expect(scene, "div", "rp-scene"))
    expect(key, "p", "rx-key")
    expect(key.children[0], "span", "rk")
    return {
        "scenes": [],
        "steps": [_step_scene(reaction) for reaction in reactions],
        "key": "".join(str(part) for part in key.children[1:]),
        "status": unit_of(expect(status, "p", "rp-status")),
    }


def _step_scene(reaction: Element) -> dict[str, Any]:
    where, art = kids(expect(reaction, "div", "rx"))
    icon, words = kids(expect(where, "div", "rx-where"))
    return {
        "whereIcon": drawing(expect(icon, "svg", "vg")),
        "where": unit_of(expect(words, "p")),
        "art": [drawing(picture) for picture in kids(expect(art, "div", "rx-art"))],
    }


def _step_text(section: Element) -> dict[str, Any]:
    kicker, heading, *rest = kids(expect(section, "section", "rp-step"))
    text: dict[str, Any] = {
        "kicker": unit_of(expect(kicker, "p", "kicker")),
        "heading": unit_of(expect(heading, "h4")),
        "paragraphs": [],
        "bond": None,
        "link": None,
        "conditions": [],
        "differs": None,
    }
    for part in rest:
        _step_part(part, text)
    return text


def _step_part(part: Element, text: dict[str, Any]) -> None:
    if part.tag == "p" and part.classes == ["rp-p"]:
        text["paragraphs"].append(unit_of(part))
    elif part.tag == "p" and part.classes == ["rp-bond"]:
        expect(part.children[0], "span", "kv-mk")
        text["bond"] = "".join(str(piece) for piece in part.children[1:])
    elif part.tag == "p" and part.classes == ["rp-link"]:
        text["link"] = unit_of(part)
    elif part.tag == "dl":
        text["conditions"] = [_condition(row) for row in kids(expect(part, "dl", "rp-cond"))]
    else:
        text["differs"] = _player_differs(part)


def _condition(row: Element) -> dict[str, str]:
    term, value = kids(expect(row, "div"))
    return {"term": unit_of(expect(term, "dt")), "value": unit_of(expect(value, "dd"))}


def _player_differs(details: Element) -> dict[str, Any]:
    summary, body = kids(expect(details, "details", "differs"))
    words = one_of(kids(expect(summary, "summary")))
    return {
        "summary": text_of(expect(words, "span")),
        "body": [unit_of(expect(paragraph, "p")) for paragraph in kids(expect(body, "div", "differs-body"))],
    }


def _chemistry(box: Element) -> dict[str, Any]:
    return {"parts": [_chemistry_part(part) for part in kids(expect(box, "div", "rp-chem"))]}


def _chemistry_part(part: Element) -> dict[str, Any]:
    if part.tag == "p":
        return {"part": "none", "unit": unit_of(expect(part, "p", "eq-none"))}
    if part.has_class("lane"):
        items = [_lane_item(item) for item in kids(expect(part, "div", "lane"))]
        return {"part": "lane", "label": part.attrs["aria-label"], "items": items}
    return {"part": "equation", "equation": equation(part)}


def _lane_item(item: Element) -> dict[str, Any]:
    if item.tag == "span" and item.classes == ["op"]:
        if text_of(item) != "+":
            raise InvalidInput(f"a lane joins species with +, not {item.text()!r}")
        return {"item": "plus"}
    if item.tag == "span":
        line, label = kids(expect(item, "span", "arr"))
        expect(line, "i", "ln")
        return {"item": "arrow", "label": text_of(expect(label, "small"))}
    return _species(expect(item, "div", "spc"))


def _species(item: Element) -> dict[str, Any]:
    swatch, name, *rest = kids(item)
    *formula, state = rest
    found = {
        "item": "species",
        "swatch": _swatch(swatch),
        "name": rich(expect(name, "span", "nm").children),
        "formula": None,
    }
    if formula:
        found["formula"] = rich(expect(formula[0], "span", "fm").children)
    return found | _state(expect(state, "span", "st"))


def _swatch(swatch: Element) -> str | dict[str, Any]:
    marks = [name for name in swatch.classes if name != "ssw"]
    expect(swatch, "span", "ssw", *marks)
    if marks:
        if len(marks) != 1 or marks[0] not in SWATCH_MARKS:
            raise InvalidInput(f"a species swatch is a colour or one of {SWATCH_MARKS}: {marks}")
        return marks[0]
    style = swatch.attrs.get("style", "")
    found = SWATCH_STYLE.fullmatch(style)
    if found is not None:
        return found.group(1)
    mixed = SWATCH_MIX.fullmatch(style)
    if mixed is None:
        raise InvalidInput(f"a species swatch style reads as a colour token or a mix of two: {swatch.attrs}")
    return {"first": mixed.group(1), "share": int(mixed.group(2)), "second": mixed.group(3)}


def _state(state: Element) -> dict[str, Any]:
    parts = state.children
    if not parts or not isinstance(parts[-1], Element) or parts[-1].tag != "a":
        return {"state": rich(parts), "cid": None}
    link = expect(parts[-1], "a", "cid")
    found = PUBCHEM_LINK.fullmatch(link.attrs["href"])
    if found is None or text_of(link) != f"CID {found.group(1)}":
        raise InvalidInput(f"a species links its PubChem record by CID: {link.attrs}")
    return {"state": rich(parts[:-1]), "cid": int(found.group(1))}


def _dip_phase(item: Element) -> dict[str, Any]:
    picture, kicker, words = kids(expect(item, "li", "vs"))
    return {
        "pose": item.attrs["data-pose"],
        "drawing": drawing(expect(picture, "svg", "vf-mini")),
        "kicker": unit_of(expect(kicker, "p", "vs-k")),
        "text": unit_of(expect(words, "p", "vs-t")),
    }


def _dip_swatch(index: int, item: Element) -> str:
    swatch, number = kids(item)
    if item.attrs["data-n"] != str(index + 1) or text_of(number) != str(index + 1):
        raise InvalidInput(f"dip {index + 1} is numbered in order")
    found = SWATCH_STYLE.fullmatch(expect(swatch, "span", "dsw").attrs["style"])
    if found is None:
        raise InvalidInput(f"dip {index + 1} has no colour token")
    return found.group(1)
