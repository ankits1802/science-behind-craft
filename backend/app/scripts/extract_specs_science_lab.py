from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.core.errors import InvalidInput

from .extract_specs_science_dom import Element
from .extract_specs_science_read import (
    drawing,
    expect,
    kids,
    note_differs,
    one_of,
    rich,
    slot,
    styled_unit,
    text_of,
    unit_of,
)

__all__ = ["choice_toggle", "experiment_lab"]

PUBCHEM_LINK = re.compile(r"https://pubchem\.ncbi\.nlm\.nih\.gov/compound/(\d+)")
HOOK = re.compile(r"data-([a-z][a-z0-9-]*)")
SWITCH_ID = re.compile(r"sw-([a-z][a-z0-9-]*)")


def experiment_lab(element: Element, nested: Mapping[int, str]) -> dict[str, Any]:
    head, *panels = kids(expect(element, "div", "wif"))
    number, pick = kids(expect(head, "div", "lab-head"))
    picker = expect(one_of(kids(expect(pick, "div", "lab-pick"))), "div", "seg")
    experiments = []
    for button, panel in zip(kids(picker), panels, strict=True):
        key = button.attrs["data-x"]
        if panel.attrs.get("data-exp") != key:
            raise InvalidInput(f"the lab's experiment {key} opens the panel of the same name")
        experiments.append({"key": key, "label": text_of(button), "toggle": slot(panel, nested)})
    return {
        "id": element.attrs["id"],
        "figure": number.attrs["data-fig"],
        "number": unit_of(expect(number, "p", "fig-no")),
        "pickerLabel": picker.attrs["aria-label"],
        "experiments": experiments,
    }


def choice_toggle(element: Element, nested: Mapping[int, str]) -> dict[str, Any]:
    text, visual = kids(expect(element, "div", "lab-panel"))
    question, choice, results, *more_text = kids(expect(text, "div", "lab-txt"))
    expect(question, "p", "switch-q")
    buttons = kids(expect(choice, "div", "seg"))
    if choice.attrs["data-choice"] != element.attrs["data-exp"]:
        raise InvalidInput("a toggle's choice belongs to its experiment")
    outcomes = kids(expect(results, "div", "lab-res"))
    return {
        "experiment": element.attrs["data-exp"],
        "questionId": question.attrs["id"],
        "question": unit_of(question),
        "options": [_option(button, outcome) for button, outcome in zip(buttons, outcomes, strict=True)],
        "textParts": [_panel_part(part, nested) for part in more_text],
        "visualParts": [_panel_part(part, nested) for part in kids(expect(visual, "div", "lab-vis"))],
    }


def _option(button: Element, outcome: Element) -> dict[str, Any]:
    value = button.attrs["data-v"]
    if outcome.attrs.get("data-res") != value:
        raise InvalidInput(f"option {value} shows the result of the same name")
    heading, *rest = kids(outcome)
    parts: list[dict[str, Any]] = []
    for part in rest:
        if part.tag == "p":
            parts.append({"part": "text", "unit": unit_of(expect(part, "p"))})
            continue
        differs = note_differs(part)
        if differs is not None:
            parts.append({"part": "differs", "differs": differs})
    return {"value": value, "label": text_of(button), "heading": unit_of(expect(heading, "h4")), "parts": parts}


def _panel_part(part: Element, nested: Mapping[int, str]) -> dict[str, Any]:
    if part.tag == "p":
        return {"part": "text", "text": styled_unit(part)}
    readers = {
        "forms": _formulas,
        "lab-same": _same,
        "stagebox": _stage_box,
        "lab-steps": _stepper,
        "switch-row": _switch,
    }
    for style, read in readers.items():
        if part.has_class(style):
            return read(part)
    if part.has_class("days"):
        return _chart(part, nested)
    if part.has_class("kv-lab-more"):
        return {"part": "more", "parts": [_panel_part(inner, nested) for inner in kids(part)]}
    raise InvalidInput(f"a toggle holds an unknown part <{part.tag} {part.attrs}>")


def _formulas(part: Element) -> dict[str, Any]:
    expect(part, "div", "forms")
    return {"part": "formulas", "option": part.attrs.get("data-forms"), "chips": [_chip(chip) for chip in kids(part)]}


def _chip(chip: Element) -> dict[str, Any]:
    formula, name, record = kids(expect(chip, "span", "formula"))
    found = {"formula": rich(expect(formula, "b").children), "name": text_of(expect(name, "span")), "cid": None}
    if record.tag == "span":
        return found | {"source": text_of(record)}
    link = PUBCHEM_LINK.fullmatch(expect(record, "a").attrs["href"])
    if link is None or text_of(record) != f"PubChem CID {link.group(1)}":
        raise InvalidInput(f"formula {found['name']!r} links its PubChem record by CID")
    return found | {"cid": int(link.group(1)), "source": None}


def _same(part: Element) -> dict[str, Any]:
    label, *paragraphs = kids(expect(part, "div", "lab-same"))
    return {
        "part": "same",
        "label": unit_of(expect(label, "p", "lk")),
        "paragraphs": [unit_of(expect(paragraph, "p")) for paragraph in paragraphs],
    }


def _chart(part: Element, nested: Mapping[int, str]) -> dict[str, Any]:
    title, plot, source = kids(expect(part, "div", "days"))
    return {
        "part": "chart",
        "title": unit_of(expect(title, "p", "chart-title", "days-t")),
        "chart": slot(one_of(kids(expect(plot, "div", "days-plot"))), nested),
        "source": unit_of(expect(source, "p", "src-line")),
    }


def _stage_box(part: Element) -> dict[str, Any]:
    picture, *note = kids(expect(part, "div", "stagebox"))
    found = {"part": "stage", "drawing": drawing(picture), "note": None, "noteHook": None}
    if note:
        words = expect(one_of(note), "p", "sb-note")
        found |= {"note": unit_of(words), "noteHook": _hook(words)}
    return found


def _stepper(part: Element) -> dict[str, Any]:
    actions, status = kids(expect(part, "div", "lab-steps"))
    button = expect(one_of(kids(expect(actions, "div", "actions"))), "button", "btn", "sm")
    return {
        "part": "stepper",
        "hook": _hook(button),
        "action": rich(button.children),
        "statusHook": _hook(expect(status, "span", "tap-day")),
        "status": text_of(status),
    }


def _switch(part: Element) -> dict[str, Any]:
    words, button = kids(expect(part, "div", "switch-row", "lab-sw"))
    label, description = kids(expect(words, "span", "sw-text"))
    found = SWITCH_ID.fullmatch(expect(label, "span", "sw-label").attrs["id"])
    hook = found.group(1) if found else ""
    if expect(button, "button", "switch").attrs.get(f"data-{hook}-sw") != "":
        raise InvalidInput(f"the switch labelled {label.attrs['id']} carries its hook")
    return {
        "part": "switch",
        "hook": hook,
        "label": rich(label.children),
        "description": text_of(expect(description, "span", "sw-desc")),
    }


def _hook(element: Element) -> str:
    hooks = [found.group(1) for name in element.attrs if (found := HOOK.fullmatch(name))]
    if len(hooks) != 1:
        raise InvalidInput(f"<{element.tag} {element.attrs}> carries one script hook, not {hooks}")
    return hooks[0]
