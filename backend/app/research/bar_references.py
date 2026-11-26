from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .chapter_keys import CHAPTER_KEYS
from .monograph_page import ChapterName, ComponentEntry, LayoutEntry, MonographContent
from .page_counts import chapter_key
from .page_report_rules import OPENING, node_text
from .spec_strings import spec_strings

__all__ = [
    "CUT",
    "KIT_GUIDES",
    "LIST_KEPT",
    "TEXT_KEPT",
    "WORKED_PREFIX",
    "KitGuide",
    "WorkedPage",
    "kit_page",
    "trimmed_spec",
    "worked_chapter",
    "worked_topic",
]

WORKED_PREFIX = "ajrakh-"
TEXT_KEPT = 160
LIST_KEPT = 3
NODE_DEPTH_KEPT = 2
UNITS_SHOWN = 16
LINE_KEPT = 140
CUT = "…"
TAG, CHILDREN = "tag", "children"
FENCE_MARK, FENCE_STAND_IN = "`", "'"
HEAD = (
    "# Kutch Ajrakh, worked: {title}\n\n"
    "Chapter {number} of {chapters} of Kutch Ajrakh's page (`{path}`), the page the owner approved, read from "
    "its live document as the worked example of how a page is thought through. {home} Its {entries} layout "
    "entries hold {units} text units and {count} components: {kinds}. Read it for the thinking, never as a "
    "template: what in Ajrakh's facts called for each figure, "
    "where it sits beside its prose and how it is built. Your craft's own facts call for figures of their own, "
    "with labels, units and facts of their own. Why Ajrakh has each kind, and which tool makes it, is in the "
    "cookbook (`cookbook/1`).\n\n"
)
ORDER_HEAD = (
    "## The chapter in order\n\n"
    "Every entry outside a component, top to bottom as the page draws it: a text unit by its id and tag with "
    f"its words cut at {LINE_KEPT} characters, a component by its label and kind (its own section follows).\n\n"
)
SPEC_NOTE = (
    f"Its spec as stored, every text past {TEXT_KEPT} characters, every list past {LIST_KEPT} items and every "
    f"drawing below {NODE_DEPTH_KEPT} levels cut where `{CUT}` stands; ids such as `u0001` are its units:"
)
NO_SPEC = "No spec is stored for it: the authored page draws it from its own markup."
NOTHING = "nothing"
GENERATED_HOME = "A generated page holds it as its `{chapter}` chapter."
NO_GENERATED_HOME = (
    "A generated page has no `{chapter}` chapter: the kinds here are the site's own or the authored page's, "
    "and the cookbook names the few a contribution reaches."
)
GENERATED_CHAPTERS = frozenset({OPENING, *CHAPTER_KEYS})


@dataclass(frozen=True)
class KitGuide:
    topic: str
    file: str
    title: str
    language: str
    holds: str


KIT_GUIDES: Mapping[str, KitGuide] = MappingProxyType(
    {
        guide.topic: guide
        for guide in (
            KitGuide(
                "kit-stylesheet",
                "monograph.css",
                "The kit's stylesheet",
                "css",
                "the stylesheet Kutch Ajrakh's page and every generated page are drawn with: the page's "
                "spread, rail and margin, every player's, card's, plate's and figure's parts, their motion and "
                "its stop under reduced motion, and the four themes through the design's tokens",
            ),
            KitGuide(
                "kit-script",
                "monograph.js",
                "The kit's player script",
                "js",
                "the one script the kit's players, steppers, toggles, labs and maps run on: how a step is "
                "chosen, played and paused, how a figure rests whole, and how every motion stops under either "
                "reduced-motion switch",
            ),
        )
    }
)
KIT_HEAD = (
    "# {title}\n\n"
    "`{file}` of the page kit, as the server holds it and the site serves it at `/monographs/kit/{file}`: "
    "{holds}. A coded figure matches it: find the part you draw by the classes its worked component's spec "
    "names (`ajrakh-<chapter>/1`), and take every colour, size and motion from the design's tokens "
    "(`system/1`), never a value copied from here.\n\n"
    "## {file}\n\n"
    "```{language}\n"
)
KIT_CLOSE = "```\n"


def worked_topic(chapter: str) -> str:
    return f"{WORKED_PREFIX}{chapter}"


@dataclass(frozen=True)
class WorkedPage:
    content: MonographContent
    specs: Mapping[str, Mapping[str, Any]]
    path: str

    def chapters(self) -> list[ChapterName]:
        return list(self.content.chapters)

    def unit_line(self, ref: str) -> str:
        unit = self.content.units.get(ref)
        if unit is None:
            return ""
        words = " ".join(node_text(unit.nodes).split()).replace(FENCE_MARK, FENCE_STAND_IN)
        return words if len(words) <= LINE_KEPT else words[:LINE_KEPT] + CUT

    def entries(self, chapter: str) -> list[LayoutEntry]:
        return [entry for entry in self.content.layout if entry.chapter == chapter]

    def components(self, chapter: str) -> list[ComponentEntry]:
        return [component for component in self.content.components if component.chapter == chapter]

    def held_units(self, component: ComponentEntry) -> list[str]:
        placed = [entry.ref for entry in self.content.layout if entry.within == component.label]
        named = [
            value
            for value in spec_strings(self.specs.get(component.label, {}))
            if value in self.content.units
        ]
        return list(dict.fromkeys([*placed, *named]))


def worked_chapter(page: WorkedPage, key: str) -> str:
    chapters = page.chapters()
    number, chapter = next((n, c) for n, c in enumerate(chapters, start=1) if c.key == key)
    entries = page.entries(key)
    top = [entry for entry in entries if entry.within is None]
    components = page.components(key)
    head = HEAD.format(
        title=chapter.title,
        number=number,
        chapters=len(chapters),
        path=page.path,
        home=_home(chapter_key(key)),
        entries=len(entries),
        units=sum(entry.kind == "unit" for entry in entries),
        count=len(components),
        kinds=_kinds(components),
    )
    lines = [_order_line(page, entry) for entry in top]
    order = ORDER_HEAD + "".join(f"{n}. {line}\n" for n, line in enumerate(lines, start=1) if line)
    sections = [_component_section(page, component, top) for component in components]
    return "\n".join([head + order, *sections])


def trimmed_spec(value: Any, depth: int = 0) -> Any:
    if isinstance(value, str):
        return value if len(value) <= TEXT_KEPT else value[:TEXT_KEPT] + CUT
    if isinstance(value, Mapping):
        node = _is_node(value)
        if node and depth >= NODE_DEPTH_KEPT:
            return {TAG: value[TAG], CHILDREN: f"{CUT} {_node_count(value) - 1} drawing nodes"}
        nested = depth + 1 if node else depth
        return {key: trimmed_spec(item, nested) for key, item in value.items()}
    if isinstance(value, list):
        kept = [trimmed_spec(item, depth) for item in value[:LIST_KEPT]]
        rest = len(value) - LIST_KEPT
        return [*kept, f"{CUT} and {rest} more"] if rest > 0 else kept
    return value


def kit_page(guide: KitGuide, text: str) -> str:
    body = text if text.endswith("\n") else text + "\n"
    return KIT_HEAD.format(**vars(guide)) + body + KIT_CLOSE


def _home(chapter: str) -> str:
    said = GENERATED_HOME if chapter in GENERATED_CHAPTERS else NO_GENERATED_HOME
    return said.format(chapter=chapter)


def _kinds(components: Sequence[ComponentEntry]) -> str:
    counted = Counter(component.kind for component in components)
    return ", ".join(f"{count} `{kind}`" for kind, count in counted.items()) or NOTHING


def _order_line(page: WorkedPage, entry: LayoutEntry) -> str:
    if entry.kind == "component":
        found = next((c for c in page.content.components if c.label == entry.ref), None)
        kind = found.kind if found is not None else "component"
        return f"`{entry.ref}` ({kind})"
    words = page.unit_line(entry.ref)
    unit = page.content.units.get(entry.ref)
    return f"`{entry.ref}` ({unit.tag}): {words}" if words and unit is not None else ""


def _component_section(page: WorkedPage, component: ComponentEntry, top: Sequence[LayoutEntry]) -> str:
    lines = [
        f"## `{component.label}`\n",
        f"- Kind `{component.kind}`, field {component.field}{_also(component.fields)}, drawn at "
        f"`{component.anchor}` of the authored page, keyed to {', '.join(component.subjects) or NOTHING}.",
        f"- Title: {component.title}",
        f"- What it is for: {component.description}",
        f"- Where it sits: {_place(page, component, top)}",
        *_unit_lines(page, component),
        "",
        *_spec_lines(page.specs.get(component.label)),
    ]
    return "\n".join(lines) + "\n"


def _also(fields: Sequence[str]) -> str:
    return f" (also {', '.join(fields)})" if fields else ""


def _place(page: WorkedPage, component: ComponentEntry, top: Sequence[LayoutEntry]) -> str:
    refs = [entry.ref for entry in top]
    if component.label not in refs:
        return "inside another component of the chapter, which places it."
    at = refs.index(component.label)
    before = next((page.unit_line(ref) for ref in reversed(refs[:at]) if page.unit_line(ref)), "")
    after = next((page.unit_line(ref) for ref in refs[at + 1 :] if page.unit_line(ref)), "")
    said = f"entry {at + 1} of the chapter's {len(refs)}"
    said += f"; after “{before}”" if before else "; no text before it"
    return said + (f"; before “{after}”." if after else "; no text after it.")


def _unit_lines(page: WorkedPage, component: ComponentEntry) -> list[str]:
    held = page.held_units(component)
    if not held:
        return ["- Its units: none of its own."]
    shown = [f"  - `{ref}`: {page.unit_line(ref) or '(no words)'}" for ref in held[:UNITS_SHOWN]]
    more = len(held) - UNITS_SHOWN
    tail = [f"  - {CUT} and {more} more."] if more > 0 else []
    return [f"- Its units ({len(held)}), each a text a reader sees:", *shown, *tail]


def _spec_lines(spec: Mapping[str, Any] | None) -> list[str]:
    if spec is None:
        return [NO_SPEC]
    shown = json.dumps(trimmed_spec(spec), ensure_ascii=False, indent=1).replace(FENCE_MARK, FENCE_STAND_IN)
    return [SPEC_NOTE, "", "```json", shown, "```"]


def _is_node(value: Mapping[str, Any]) -> bool:
    return isinstance(value.get(TAG), str)


def _node_count(node: Mapping[str, Any]) -> int:
    children = node.get(CHILDREN)
    if not isinstance(children, list):
        return 1
    return 1 + sum(_node_count(child) for child in children if isinstance(child, Mapping))
