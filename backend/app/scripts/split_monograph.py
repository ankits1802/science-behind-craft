import argparse
import html
import itertools
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from app.core.errors import InvalidInput
from app.research.monograph_document import fragment_file_name
from app.research.monograph_page import (
    COMPONENT_SLOT,
    KIT_SLOT,
    SLOT_PATTERN,
    UNIT_SLOT,
    MonographContent,
    PageParts,
    assemble_template,
    keyed_kit,
    kit_slot_key,
    kit_source,
    slot,
)
from app.services.monograph_document import (
    FRAGMENTS_FOLDER,
    KIT_DIR,
    MONOGRAPHS_DIR,
    TEMPLATE_FILE,
    monograph_content,
    monograph_shell,
    page_parts,
)

TAG = re.compile(
    r"<!--.*?-->|<(?P<close>/?)(?P<name>[a-zA-Z][a-zA-Z0-9:-]*)"
    r"(?P<attrs>(?:\s+[^\s\"'>/=]+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s\"'=<>`]+))?)*)\s*(?P<empty>/?)>",
    re.S,
)
ATTRIBUTE = re.compile(r"([^\s\"'>/=]+)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'=<>`]+)))?")
ANCHOR = re.compile(r'^(?:#(?P<id>[A-Za-z0-9_-]+)|\[(?P<attr>[a-z-]+)="(?P<value>[^"]*)"\])$')
VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
RAW_TEXT = frozenset({"script", "style"})
STYLE = "style"
SCRIPT = "script"
HEAD_END = "</head>"
SCRIPT_KEPT_BY = frozenset({"type", "src"})
KIT_PART_NAMES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {"monograph.css": ("page", "release-fixes"), "monograph.js": ("page", "boxes")}
)
KIT_ELEMENTS: Mapping[str, str] = MappingProxyType({"monograph.css": STYLE, "monograph.js": SCRIPT})


@dataclass(frozen=True)
class Tag:
    name: str
    start: int
    end: int
    closing: bool
    empty: bool
    attributes: Mapping[str, str]


@dataclass(frozen=True)
class Span:
    start: int
    end: int

    def holds(self, other: Span) -> bool:
        return self.start <= other.start and other.end <= self.end


@dataclass(frozen=True)
class SplitPage:
    shell: str
    fragments: dict[str, str]
    kit: dict[str, str]

    def parts(self) -> PageParts:
        return PageParts(fragments=self.fragments, kit=keyed_kit(self.kit))


def split_template(template: str, content: MonographContent) -> SplitPage:
    found = tags(template)
    spans = {c.label: anchor_span(found, c.anchor, c.label) for c in content.components}
    held = holders(spans)
    check_layout(template, content, spans, held)
    blocks = kit_blocks(template, found, list(spans.values()))
    replacements = [(spans[label], slot(COMPONENT_SLOT, label)) for label, h in held.items() if h is None]
    replacements += [(span, slot(KIT_SLOT, key)) for key, span in blocks.items()]
    return SplitPage(
        shell=_replaced(template, Span(0, len(template)), replacements),
        fragments={label: _fragment(template, label, spans, held) for label in spans},
        kit=_kit_sources(template, blocks),
    )


def tags(text: str) -> list[Tag]:
    found: list[Tag] = []
    position = 0
    while (match := TAG.search(text, position)) is not None:
        position = match.end()
        if match.group("name") is None:
            continue
        name = match.group("name").lower()
        closing = match.group("close") == "/"
        empty = not closing and (name in VOID_ELEMENTS or match.group("empty") == "/")
        attributes = {} if closing else _attributes(match.group("attrs"))
        found.append(Tag(name, match.start(), match.end(), closing, empty, attributes))
        if name in RAW_TEXT and not closing and not empty:
            position = text.index(f"</{name}>", position)
    return found


def anchor_span(found: Sequence[Tag], anchor: str, label: str) -> Span:
    matched = ANCHOR.match(anchor)
    if matched is None:
        raise InvalidInput(f'The anchor {anchor} of {label} is neither #id nor [attribute="value"]')
    if matched.group("id"):
        name, value = "id", matched.group("id")
    else:
        name, value = matched.group("attr"), matched.group("value")
    hits = [i for i, tag in enumerate(found) if not tag.closing and tag.attributes.get(name) == value]
    if len(hits) != 1:
        raise InvalidInput(f"The anchor {anchor} of {label} selects {len(hits)} elements, not one")
    return element_span(found, hits[0])


def element_span(found: Sequence[Tag], index: int) -> Span:
    opening = found[index]
    if opening.empty:
        return Span(opening.start, opening.end)
    depth = 0
    for tag in found[index:]:
        if tag.name != opening.name or tag.empty:
            continue
        depth += -1 if tag.closing else 1
        if depth == 0:
            return Span(opening.start, tag.end)
    raise InvalidInput(f"The <{opening.name}> at {opening.start} is never closed")


def holders(spans: Mapping[str, Span]) -> dict[str, str | None]:
    return {label: _innermost(spans, span, label) for label, span in spans.items()}


def check_layout(
    template: str, content: MonographContent, spans: Mapping[str, Span], held: Mapping[str, str | None]
) -> None:
    placed = dict(held)
    for found in SLOT_PATTERN.finditer(template):
        if found.group(1) == UNIT_SLOT:
            placed[found.group(2)] = _innermost(spans, Span(found.start(), found.end()), None)
    differing = [entry.ref for entry in content.layout if placed.get(entry.ref, entry.within) != entry.within]
    if differing:
        raise InvalidInput(f"The layout places these inside other components than the page does: {differing}")


def kit_blocks(template: str, found: Sequence[Tag], components: Sequence[Span]) -> dict[str, Span]:
    head_end = template.index(HEAD_END)
    blocks: dict[str, Span] = {}
    for file_name, element in KIT_ELEMENTS.items():
        bodies = [
            Span(tag.end, closing.start)
            for tag, closing in itertools.pairwise(found)
            if tag.name == element
            and not tag.closing
            and _page_wide(tag, head_end)
            and not any(span.holds(Span(tag.start, closing.end)) for span in components)
        ]
        names = KIT_PART_NAMES[file_name]
        if len(bodies) != len(names):
            raise InvalidInput(
                f"The page has {len(bodies)} page-wide {element} blocks; the kit names {len(names)}"
            )
        blocks |= {kit_slot_key(file_name, name): body for name, body in zip(names, bodies, strict=True)}
    return blocks


def write_split(slug: str, split: SplitPage) -> list[str]:
    folder = MONOGRAPHS_DIR / slug / FRAGMENTS_FOLDER
    folder.mkdir(exist_ok=True)
    KIT_DIR.mkdir(exist_ok=True)
    targets = {MONOGRAPHS_DIR / slug / TEMPLATE_FILE: split.shell}
    targets |= {folder / fragment_file_name(label): text for label, text in split.fragments.items()}
    targets |= {KIT_DIR / file_name: source for file_name, source in split.kit.items()}
    for path, text in targets.items():
        path.write_bytes(text.encode("utf-8"))
    return [path.name for path in targets]


def current_template(slug: str) -> str:
    shell = monograph_shell(slug)
    if not any(kind in (COMPONENT_SLOT, KIT_SLOT) for kind, _ in SLOT_PATTERN.findall(shell)):
        return shell
    return assemble_template(shell, page_parts(monograph_content(slug)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="split_monograph")
    parser.add_argument("slug", help="the monograph's folder, such as Kutch-Ajrakh")
    args = parser.parse_args(argv)
    template = current_template(args.slug)
    split = split_template(template, monograph_content(args.slug))
    if assemble_template(split.shell, split.parts()) != template:
        raise InvalidInput("The shell, fragments and kit do not rebuild the template")
    written = write_split(args.slug, split)
    print(json.dumps({"ok": True, "fragments": len(split.fragments), "files": len(written)}))
    return 0


def _page_wide(tag: Tag, head_end: int) -> bool:
    if tag.name == STYLE:
        return True
    return tag.start > head_end and not SCRIPT_KEPT_BY & set(tag.attributes)


def _innermost(spans: Mapping[str, Span], inner: Span, label: str | None) -> str | None:
    outer = [other for other, span in spans.items() if other != label and span.holds(inner)]
    return max(outer, key=lambda other: spans[other].start) if outer else None


def _fragment(template: str, label: str, spans: Mapping[str, Span], held: Mapping[str, str | None]) -> str:
    inner = [(spans[child], slot(COMPONENT_SLOT, child)) for child, holder in held.items() if holder == label]
    return _replaced(template, spans[label], inner)


def _kit_sources(template: str, blocks: Mapping[str, Span]) -> dict[str, str]:
    sources: dict[str, str] = {}
    for file_name, names in KIT_PART_NAMES.items():
        parts = {name: _text_of(template, blocks[kit_slot_key(file_name, name)]) for name in names}
        sources[file_name] = kit_source(parts, file_name=file_name)
    return sources


def _replaced(text: str, span: Span, replacements: Sequence[tuple[Span, str]]) -> str:
    pieces: list[str] = []
    position = span.start
    for inner, replacement in sorted(replacements, key=lambda pair: pair[0].start):
        pieces += [text[position : inner.start], replacement]
        position = inner.end
    pieces.append(text[position : span.end])
    return "".join(pieces)


def _text_of(text: str, span: Span) -> str:
    return text[span.start : span.end]


def _attributes(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for match in ATTRIBUTE.finditer(text):
        value = next((group for group in match.groups()[1:] if group is not None), "")
        found[match.group(1).lower()] = html.unescape(value)
    return found


if __name__ == "__main__":
    raise SystemExit(main())
