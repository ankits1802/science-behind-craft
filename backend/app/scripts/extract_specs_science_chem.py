from __future__ import annotations

from typing import Any

from app.core.errors import InvalidInput

from .extract_specs_science_dom import Element
from .extract_specs_science_read import expect, kids, one_of, only, rich, text_of, unit_of

__all__ = ["equation", "equation_line", "figure_head", "grouped_line", "species", "tick_count"]

ARROW = "→"
PLUS = "+"


def figure_head(paragraphs: list[Element]) -> dict[str, Any]:
    number, title, *rest = paragraphs
    expect(number, "p", "fig-no")
    expect(title, "p", "chart-title")
    head = {
        "figure": number.attrs.get("data-fig"),
        "number": unit_of(number),
        "title": unit_of(title),
        "titleId": title.attrs.get("id"),
        "dek": None,
    }
    if rest:
        head["dek"] = unit_of(only_paragraph(rest, "chart-dek"))
    return head


def only_paragraph(rest: list[Element], style: str) -> Element:
    if len(rest) != 1 or rest[0].tag != "p" or style not in rest[0].classes:
        raise InvalidInput(f"a figure head ends with one p.{style}, found {[(e.tag, e.attrs) for e in rest]}")
    return rest[0]


def species(element: Element) -> dict[str, Any]:
    expect(element, "span", "sp")
    parts = kids(element)
    formula = expect(parts[0], "b")
    named = {"formula": rich(formula.children), "name": None}
    if len(parts) == 2:
        named["name"] = text_of(expect(parts[1], "small"))
    elif len(parts) != 1:
        raise InvalidInput(f"a species is a formula and at most a name: {element.attrs}")
    return named


def equation_line(element: Element) -> dict[str, Any]:
    expect(element, "div", "eq-line")
    left, right = kids(element)
    expect(left, "span", "side")
    expect(right, "span", "side", "prod")
    arrow, *products = kids(right)
    _operator(arrow, ARROW, "op", "arrow")
    return {"reactants": _terms(kids(left)), "products": _terms(products)}


def grouped_line(element: Element) -> dict[str, Any]:
    left, right = kids(element)
    first, *more = kids(expect(left, "span", "side"))
    reactants = [species(first), *(_grouped(group, PLUS) for group in more)]
    groups = kids(expect(right, "span", "side"))
    products = [_grouped(groups[0], ARROW), *(_grouped(group, PLUS) for group in groups[1:])]
    return {"reactants": reactants, "products": products}


def equation(element: Element) -> dict[str, Any]:
    style = [name for name in element.classes if name != "eq"]
    expect(element, "div", "eq", *style)
    line, *foot = kids(element)
    spec = {
        "label": element.attrs["aria-label"],
        "style": " ".join(style) or None,
        "line": equation_line(line),
        "atoms": None,
        "notes": [],
    }
    if foot:
        spec |= _foot(expect(one_of(foot), "div", "eq-foot"))
    return spec


def tick_count(element: Element) -> str:
    expect(element, "p", "eq-count")
    tick, *rest = element.children
    if not isinstance(tick, Element) or rest == [] or not all(isinstance(part, str) for part in rest):
        raise InvalidInput("an atom count is a tick and its line")
    expect(only(expect(tick, "span", "ok")), "svg")
    return "".join(str(part) for part in rest)


def _foot(foot: Element) -> dict[str, Any]:
    table, *notes = kids(foot)
    found: dict[str, Any] = {"atoms": _atoms(expect(table, "table", "atoms"))}
    if notes:
        paragraphs = kids(expect(one_of(notes), "div", "eq-notes"))
        found["notes"] = [unit_of(expect(paragraph, "p", "eq-note")) for paragraph in paragraphs]
    return found


def _atoms(table: Element) -> dict[str, Any]:
    caption, head, body = kids(table)
    header = only(expect(head, "thead"))
    rows = kids(expect(body, "tbody"))
    return {
        "caption": text_of(expect(caption, "caption")),
        "head": [unit_of(cell) for cell in kids(header)],
        "rows": [_atom_row(row) for row in rows],
    }


def _atom_row(row: Element) -> dict[str, Any]:
    element, left, right, balanced = kids(row)
    expect(balanced, "td", "ok")
    return {"element": unit_of(element), "left": unit_of(left), "right": unit_of(right)}


def _terms(elements: list[Element]) -> list[dict[str, Any]]:
    found = []
    for index, element in enumerate(elements):
        if index % 2:
            _operator(element, PLUS, "op")
        else:
            found.append(species(element))
    return found


def _grouped(group: Element, sign: str) -> dict[str, Any]:
    operator, term = kids(expect(group, "span", "grp"))
    _operator(operator, sign, "op")
    return species(term)


def _operator(element: Element, sign: str, *classes: str) -> None:
    expect(element, "span", *classes)
    if text_of(element) != sign:
        raise InvalidInput(f"expected the operator {sign!r}, found {element.text()!r}")
