from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import Field

from app.core.errors import InvalidInput

from .base import ContractModel
from .vocabulary import Discipline, PieceKind

__all__ = [
    "MONOGRAPH_SCHEMA_VERSION",
    "SLOT_PATTERN",
    "CitedSource",
    "ComponentEntry",
    "LayoutEntry",
    "MonographContent",
    "Quote",
    "TextUnit",
    "render_nodes",
    "render_page",
    "slot",
]

MONOGRAPH_SCHEMA_VERSION = 1
COMPONENT_LABEL_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*(/[a-z0-9]+(-[a-z0-9]+)*){2,}$"
SLOT_PATTERN = re.compile(r'<kv-slot (unit|data)="([A-Za-z0-9._-]+)"></kv-slot>')
UNIT_SLOT = "unit"
DATA_SLOT = "data"
CITES_DATA = "kv-cites"
ITALIC_ROLES = ("loc", "bot", "ring", "on")
MARK_TAGS = {"b": "b", "sub": "sub", "sup": "sup", "mark": "mark"}
SENTENCE_ATTRS = (("src", "data-src"), ("sid", "data-sid"), ("pair", "data-pair"))
LINK_ATTRS = (("rel", "rel"), ("target", "target"), ("ask", "data-ask"), ("lang", "lang"))

Node = str | dict[str, Any]


class CitedSource(ContractModel):
    number: int = Field(ge=1)
    title: str
    full_title: str | None
    publisher: str | None
    year: int | None
    grade: str | None
    url: str | None
    extra: str | None
    dossier_source_id: str | None


class Quote(ContractModel):
    source: str
    locator: str | None
    quote: str | None


class TextUnit(ContractModel):
    chapter: str
    tag: str
    field: Discipline | None
    nodes: list[Any]
    claim_ids: list[str]


class ComponentEntry(ContractModel):
    label: str = Field(pattern=COMPONENT_LABEL_PATTERN)
    chapter: str
    anchor: str
    kind: PieceKind
    title: str
    description: str
    field: Discipline
    fields: list[Discipline]
    subjects: list[str]


class LayoutEntry(ContractModel):
    chapter: str
    kind: Literal["unit", "component"]
    ref: str
    within: str | None = None


class MonographContent(ContractModel):
    schema_version: Literal[1] = MONOGRAPH_SCHEMA_VERSION
    craft_slug: str
    sources: dict[str, CitedSource]
    citations: dict[str, list[Quote]]
    citation_claims: dict[str, list[str]]
    data: dict[str, Any]
    units: dict[str, TextUnit]
    components: list[ComponentEntry]
    layout: list[LayoutEntry]


def slot(kind: str, key: str) -> str:
    return f'<kv-slot {kind}="{key}"></kv-slot>'


def render_page(template: str, content: MonographContent) -> str:
    sources = content.sources

    def fill(found: re.Match[str]) -> str:
        kind, key = found.group(1), found.group(2)
        if kind == UNIT_SLOT:
            unit = content.units.get(key)
            if unit is None:
                raise InvalidInput(f"The template has a slot for unit {key}, which the content lacks")
            return render_nodes(unit.nodes, sources)
        if kind == DATA_SLOT:
            return _data(key, content)
        raise InvalidInput(f"No slot kind {kind!r}")

    return SLOT_PATTERN.sub(fill, template)


def render_nodes(nodes: Sequence[Node], sources: Mapping[str, CitedSource]) -> str:
    return "".join(_node(node, sources) for node in nodes)


def _node(node: Node, sources: Mapping[str, CitedSource]) -> str:
    if isinstance(node, str):
        return html.escape(node, quote=False)
    mark = node.get("m")
    inner = render_nodes(node.get("c", []), sources)
    if mark == "s":
        extra = f" {node['cls']}" if node.get("cls") else ""
        return f'<span class="s{extra}"{_attrs(node, SENTENCE_ATTRS)}>{inner}</span>'
    if mark == "span":
        return (
            f'<span class="{html.escape(node["cls"])}">{inner}</span>'
            if node.get("cls")
            else f"<span>{inner}</span>"
        )
    if mark == "cite":
        return f'<span class="nw">{inner}{_cite_button(node, sources)}</span>'
    if mark == "i":
        role = node.get("role")
        if role is not None and role not in ITALIC_ROLES:
            raise InvalidInput(f"No italic role {role!r}")
        return f'<i class="{role}">{inner}</i>' if role else f"<i>{inner}</i>"
    if mark in MARK_TAGS:
        tag = MARK_TAGS[mark]
        return f"<{tag}>{inner}</{tag}>"
    if mark == "link":
        if node.get("cls"):
            return f'<a class="{html.escape(node["cls"])}" href="{html.escape(node["href"])}">{inner}</a>'
        return f'<a href="{html.escape(node["href"])}"{_attrs(node, LINK_ATTRS)}>{inner}</a>'
    if mark == "figref":
        return f'<span class="kv-figref" data-figref="{html.escape(node["ref"])}">{inner}</span>'
    raise InvalidInput(f"No inline mark {mark!r}")


def _attrs(node: Mapping[str, Any], names: Sequence[tuple[str, str]]) -> str:
    return "".join(
        f' {attribute}="{html.escape(node[key])}"' for key, attribute in names if node.get(key) is not None
    )


def _cite_button(node: Mapping[str, Any], sources: Mapping[str, CitedSource]) -> str:
    keys = list(node["g"])
    missing = [key for key in keys if key not in sources]
    if missing:
        raise InvalidInput(f"Citation {node['key']} names unknown sources {missing}")
    shown = sorted({sources[key].number: sources[key] for key in keys}.items())
    numbers = [str(number) for number, _ in shown]
    label = f"Source {numbers[0]}" if len(numbers) == 1 else f"Sources {_listed(numbers)}"
    described = "; ".join(source.title for _, source in shown)
    return (
        f'<button class="kcite" type="button" data-c="{html.escape(node["key"])}" '
        f'data-g="{" ".join(keys)}" aria-haspopup="dialog" aria-expanded="false" '
        f'aria-label="{label}" aria-description="{html.escape(described)}">{",".join(numbers)}</button>'
    )


def _listed(numbers: Sequence[str]) -> str:
    return numbers[0] if len(numbers) == 1 else f"{', '.join(numbers[:-1])} and {numbers[-1]}"


def _data(key: str, content: MonographContent) -> str:
    if key == CITES_DATA:
        value: Any = {
            "s": {
                g: [
                    s.number,
                    s.title,
                    s.full_title,
                    s.publisher,
                    s.year,
                    s.grade,
                    s.url,
                    s.extra,
                ]
                for g, s in content.sources.items()
            },
            "c": {
                key: [[q.source, q.locator, q.quote] for q in quotes]
                for key, quotes in content.citations.items()
            },
        }
    elif key in content.data:
        value = content.data[key]
    else:
        raise InvalidInput(f"The template has a slot for data {key}, which the content lacks")
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
