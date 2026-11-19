import argparse
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any
from urllib.parse import parse_qs, urlsplit

from app.research.component_specs_tools import SPEC_MODELS_TOOLS
from app.research.monograph_document import spec_file_name
from app.research.monograph_page import MonographContent
from app.scripts.build_monograph import MONOGRAPHS_DIR, TEMPLATE_FILE, monograph_content
from app.scripts.extract_specs_tools_markup import (
    Element,
    anchor_test,
    has_attr,
    has_class,
    has_slot,
    inline_nodes,
    parse_markup,
    slot_ref,
    text_of,
)

SPECS_DIR = "specs"
TOOL_SLUGS = ("Kutch-Ajrakh",)
LANGUAGE_STATUSES = re.compile(r"\{ en: '[^']*', hi: '([^']*)', ur: '([^']*)' \}\[lang\]")
NARROW_SPACE = "\u202f"


@dataclass(frozen=True)
class Source:
    root: Element
    content: MonographContent
    script: str

    def component_root(self, label: str) -> Element:
        anchor = next(c.anchor for c in self.content.components if c.label == label)
        return self.root.one(anchor_test(anchor))

    def placed_below(self, element: Element) -> list[str]:
        tests = [(component.label, anchor_test(component.anchor)) for component in self.content.components]
        inner = element.all(lambda e: e is not element)
        return [label for found in inner for label, test in tests if test(found)]

    def source_key(self, number: int) -> str:
        return next(key for key, source in self.content.sources.items() if source.number == number)


def explainer_spec(source: Source, root: Element) -> dict[str, Any]:
    cards_box = root.one(has_class("hc-cards"))
    return {
        "kicker": slot_ref(root.one(has_class("chapter-no"))),
        "title": slot_ref(root.one(lambda e: e.tag == "h3")),
        "sentence": slot_ref(root.one(has_class("hc-sent"))),
        "keys": [slot_ref(item) for item in root.one(has_class("hc-keys")).all(lambda e: e.tag == "li")],
        "cardsLabel": cards_box.attrs["aria-label"],
        "cards": [_quote_card(source, card) for card in cards_box.all(has_class("qcard"))],
    }


def _quote_card(source: Source, card: Element) -> dict[str, Any]:
    number = card.one(lambda e: e.tag == "b").own_text().strip()
    quote = card.one(lambda e: e.tag == "blockquote")
    own = {"quoteUnit": slot_ref(quote)} if has_slot(quote) else {"quote": quote.own_text().strip()}
    caption = card.one(lambda e: e.tag == "figcaption")
    byline = next(c for c in caption.children if isinstance(c, Element) and c.tag == "span")
    return {
        "source": source.source_key(int(number)),
        "byline": byline.text().strip(),
        **own,
        "locator": card.one(has_class("loc")).own_text().strip(),
        "keyed": bool(card.all(has_class("mk"))),
    }


def quiz_spec(source: Source, root: Element) -> dict[str, Any]:
    head = root.one(has_class("end-h"))
    return {
        "title": slot_ref(head.one(lambda e: e.tag == "h3")),
        "kicker": head.one(has_class("kicker")).text().strip(),
        "dek": slot_ref(root.one(has_class("end-dek"))),
        "score": slot_ref(root.one(has_attr("id", "quiz-score"))),
        "status": slot_ref(root.one(has_attr("id", "quiz-status"))),
        "nextLabel": root.one(has_attr("id", "quiz-next")).text().strip(),
        "questions": [_quiz_question(item) for item in source.content.data["kv-data"]["quiz"]],
    }


def _quiz_question(item: Mapping[str, Any]) -> dict[str, Any]:
    button = parse_markup(item["cite"]).one(has_class("kcite"))
    return {
        "before": item["pre"],
        "after": item["post"],
        "cite": {"key": button.attrs["data-c"], "sources": button.attrs["data-g"].split()},
        "choices": [
            {
                "term": o["term"],
                "right": o["right"],
                "sentence": inline_nodes(parse_markup(o["html"]).children),
            }
            for o in item["opts"]
        ],
    }


def ask_next_spec(source: Source, root: Element) -> dict[str, Any]:
    links = root.all(lambda e: e.tag == "a")
    crafts = {parse_qs(urlsplit(link.attrs["href"]).query)["craft"][0] for link in links}
    if len(crafts) != 1:
        raise ValueError(f"ask-next links name {sorted(crafts)}, not one craft")
    return {
        "craft": crafts.pop(),
        "action": root.all(has_class("ago"))[0].text().strip(),
        "questions": [link.attrs["data-ask"] for link in links],
    }


def reading_level_spec(source: Source, root: Element) -> dict[str, Any]:
    return {
        "level": root.one(has_attr("data-level")).attrs["data-level"],
        "summary": root.one(has_class("kv-alt-s")).text().strip(),
        "detail": root.one(has_class("kv-alt-d")).text().strip(),
        "title": slot_ref(root.one(has_class("twin-t"))),
        "lede": slot_ref(root.one(has_class("twin-lede"))),
    }


def language_switch_spec(source: Source, root: Element) -> dict[str, Any]:
    buttons = root.one(has_class("lang-seg")).all(has_attr("data-lang"))
    found = LANGUAGE_STATUSES.search(source.script)
    if found is None:
        raise ValueError("the page script names no status for each answer language")
    statuses = [root.one(has_attr("id", "lang-status")).text().strip(), *found.groups()]
    panels = [
        panel for panel in root.all(has_attr("data-lang-panel")) if panel.attrs["data-lang-panel"] != "en"
    ]
    return {
        "label": root.one(has_class("lang-bar")).one(has_class("t-label")).text().strip(),
        "options": [_language_option(b, status) for b, status in zip(buttons, statuses, strict=True)],
        "english": slot_ref(root.one(has_attr("data-lang-panel", "en"))),
        "panels": [_language_panel(source, panel) for panel in panels],
    }


def _language_option(button: Element, status: str) -> dict[str, Any]:
    direction = "rtl" if button.all(has_attr("dir", "rtl")) else "ltr"
    return {
        "lang": button.attrs["data-lang"],
        "name": button.text().strip(),
        "direction": direction,
        "status": status,
    }


def _language_panel(source: Source, panel: Element) -> dict[str, Any]:
    main = panel.one(has_class("main"))
    actions = main.one(has_class("direct-actions"))
    body = next(c for c in main.children if isinstance(c, Element) and c.tag == "p" and not c.classes())
    figures = source.placed_below(main)
    aside = panel.one(lambda e: e.tag == "aside")
    plates = aside.all(has_class("margin-plate"))
    return {
        "lang": panel.attrs["data-lang-panel"],
        "direction": panel.attrs.get("dir", "ltr"),
        "provenance": _provenance(panel.one(has_class("provenance"))),
        "lede": inline_nodes(main.one(has_class("t-lede")).children),
        "actions": {
            "save": text_of(actions, has_attr("data-save")),
            "cite": text_of(actions, has_attr("data-kv-goto")),
        },
        "section": {
            "kind": text_of(main, has_class("sec-kind")),
            "title": slot_ref(main.one(has_class("t-h2"))),
            "body": inline_nodes(body.children),
        },
        "figure": figures[0] if figures else None,
        "notes": [slot_ref(item) for item in aside.one(lambda e: e.tag == "ul").all(lambda e: e.tag == "li")],
        "plate": _margin_plate(plates[0]) if plates else None,
    }


def _provenance(rail: Element) -> dict[str, Any]:
    parts = [child for child in rail.children if isinstance(child, Element)]
    strip = rail.one(has_class("rel-strip"))
    link = rail.one(lambda e: e.tag == "a")
    listen = rail.one(has_attr("data-listen-open"))
    words = listen.one(lambda e: e.tag == "span" and not e.attrs)
    return {
        "items": [part.text().strip() for part in parts[: parts.index(strip)]],
        "reliability": {
            "label": strip.attrs["aria-label"],
            "grades": [_grade(g) for g in strip.all(has_class("rs-g"))],
        },
        "monograph": {"text": link.text().strip(), "href": link.attrs["href"]},
        "answered": parts[parts.index(link) + 1].text().strip(),
        "listen": {
            "label": str(words.children[0]).strip(),
            "minutes": int(text_of(listen, has_attr("data-listen-min"))),
            "unit": str(words.children[-1]).strip(),
        },
    }


def _grade(group: Element) -> dict[str, Any]:
    grade = next(name for name in group.one(has_class("rel")).classes() if name != "rel")
    return {"grade": grade, "count": int(group.own_text().replace(NARROW_SPACE, " ").split()[-1])}


def _margin_plate(box: Element) -> dict[str, Any]:
    picture = box.one(lambda e: e.tag == "img")
    wrapper = box.one(has_class("cap")).one(
        lambda e: e.tag == "span" and e.classes()[:1] not in (["s"], ["nw"])
    )
    return {
        "src": picture.attrs["src"],
        "width": int(picture.attrs["width"]),
        "height": int(picture.attrs["height"]),
        "alt": picture.attrs["alt"],
        "caption": inline_nodes(wrapper.children),
        "credit": slot_ref(box.one(has_class("credit"))),
    }


def generator_spec(source: Source, root: Element) -> dict[str, Any]:
    state = root.one(has_attr("id", "gen-state"))
    sections = root.all(has_class("gsec"))
    films = source.placed_below(root.one(has_attr("id", "gen-secs")))
    jobs = root.one(has_class("jobs")).all(lambda e: e.tag == "li")
    return {
        "stage": {"state": state.own_text().strip(), "detail": text_of(state, has_attr("id", "gen-sub"))},
        "switchLabel": text_of(root, has_class("sw-label")),
        "switchDetail": text_of(root, has_class("sw-desc")),
        "replay": text_of(root, has_attr("id", "gen-reset")),
        "status": text_of(sections[0], has_class("gsec-st")),
        "sections": [_generator_section(source, section) for section in sections],
        "film": next((label for label in films if label not in _section_media(source, sections)), None),
        "railTitle": slot_ref(root.one(has_class("mr-h"))),
        "railDetail": slot_ref(root.one(has_class("mr-dek"))),
        "jobs": [
            {"title": text_of(job, has_class("jt")), "state": text_of(job, has_class("js"))} for job in jobs
        ],
    }


def _section_media(source: Source, sections: list[Element]) -> set[str]:
    return {label for section in sections for label in source.placed_below(section)}


def _generator_section(source: Source, section: Element) -> dict[str, Any]:
    title = section.one(has_class("gsec-t"))
    text = section.one(has_class("gsec-text"))
    body = section.one(has_class("gsec-body"))
    return {
        "number": int(section.attrs["data-n"]),
        **({"titleUnit": slot_ref(title)} if has_slot(title) else {"title": title.text().strip()}),
        "kind": text_of(section, has_class("gsec-k")),
        **({"textUnit": slot_ref(text)} if has_slot(text) else {"text": inline_nodes(text.children)}),
        "media": source.placed_below(section.one(has_class("gsec-media"))),
        "split": "split" in body.classes(),
    }


EXTRACTORS: Mapping[str, Callable[[Source, Element], dict[str, Any]]] = MappingProxyType(
    {
        "explainer": explainer_spec,
        "quiz": quiz_spec,
        "ask_next": ask_next_spec,
        "language_switch": language_switch_spec,
        "reading_level": reading_level_spec,
        "generator": generator_spec,
    }
)


def tool_specs(slug: str) -> dict[str, dict[str, Any]]:
    template = (MONOGRAPHS_DIR / slug / TEMPLATE_FILE).read_bytes().decode("utf-8")
    source = Source(parse_markup(template), monograph_content(slug), template)
    specs: dict[str, dict[str, Any]] = {}
    for component in source.content.components:
        extract = EXTRACTORS.get(component.kind)
        if extract is not None:
            raw = extract(source, source.component_root(component.label))
            model = SPEC_MODELS_TOOLS[component.kind].model_validate(raw)
            specs[component.label] = model.model_dump(mode="json", by_alias=True, exclude_none=True)
    return specs


def spectext_of(spec: Mapping[str, Any]) -> str:
    return json.dumps(spec, ensure_ascii=False, indent=2) + "\n"


def stale_specs(slug: str) -> list[str]:
    folder = MONOGRAPHS_DIR / slug / SPECS_DIR
    return [
        label
        for label, spec in tool_specs(slug).items()
        if not (folder / spec_file_name(label)).is_file()
        or (folder / spec_file_name(label)).read_bytes().decode("utf-8") != spectext_of(spec)
    ]


def write_specs(slug: str) -> list[str]:
    folder = MONOGRAPHS_DIR / slug / SPECS_DIR
    folder.mkdir(exist_ok=True)
    specs = tool_specs(slug)
    for label, spec in specs.items():
        (folder / spec_file_name(label)).write_bytes(spectext_of(spec).encode("utf-8"))
    return sorted(specs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="extract_specs_tools")
    parser.add_argument(
        "--check", action="store_true", help="report tool specs that differ from their extraction"
    )
    args = parser.parse_args(argv)
    if args.check:
        stale = [label for slug in TOOL_SLUGS for label in stale_specs(slug)]
        print(json.dumps({"ok": not stale, "stale": stale}))
        return 1 if stale else 0
    print(json.dumps({"ok": True, "written": [label for slug in TOOL_SLUGS for label in write_specs(slug)]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
