import re
from collections.abc import Iterable, Mapping
from pathlib import Path

import pytest

from app.api.mcp_guides import GUIDES, bar_text, guide_sheet, guide_sheets
from app.api.mcp_page_texts import ADD, PREVIEW, READ_NEXT, REVIEWED, SUBMITTED
from app.api.mcp_protocol import SERVER_INSTRUCTIONS
from app.api.mcp_tools import TOOLS
from app.data.skill_library import DESIGN_SKILL, SKILL_FILES, reference_text, skill_file_text
from app.models.component_kinds import (
    AUTHORED_ART_KINDS,
    AUTHORED_SCRIPT_KINDS,
    COMPONENT_KINDS,
    DECLARED_ONLY_KINDS,
    DOCUMENT_KINDS,
    GENERAL_KINDS,
    PAGE_TOOL_KINDS,
)
from app.research.bar_references import CUT, KIT_GUIDES, trimmed_spec, worked_topic
from app.research.component_specs import CONTRIBUTABLE_KINDS
from app.services.bar_references import worked_page, worked_text
from app.services.compose_components import COMPOSED_KINDS
from app.services.monograph_document import kit_sources

REPOSITORY = Path(__file__).resolve().parents[3]
SITE_SKILLS = REPOSITORY / "frontend" / "public" / "skills"
CLAUDE_SKILLS = REPOSITORY / ".claude" / "skills"
ENTRY = re.compile(r"^## `(?P<kind>[a-z0-9_]+)`\n(?P<body>.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
STEP = re.compile(r"^(?P<number>\d+)\. \*\*(?P<title>[^*]+)\*\*", re.MULTILINE)
ADDRESS = re.compile(r"`(?P<address>[a-z0-9-]+/[1-9][0-9]*)`")
LABEL = re.compile(r"`(?P<label>[a-z0-9-]+(?:/[a-z0-9-]+){2,})`")
LINES = ("Shows", "When a page needs it", "In Kutch Ajrakh", "Made by", "Facts", "Place", "Check")
STEPS = (
    "Find the craft's story in its facts.",
    "Decide what a reader must see and do to understand it.",
    "See how Kutch Ajrakh answered the same questions.",
    "Open the draft.",
    "Find what the story lacks.",
    "Design and build each figure.",
    "Give the pictures, the masthead first.",
    "Lay it out.",
    "Preview and judge it as a reader.",
    "Propose, then the next round.",
)
TOOLS_IN_ORDER = (
    "`get_page`",
    "`get_facts`",
    "`edit_draft`",
    "`propose_facts`",
    "`compose_component`",
    "`preview_page`",
    "`propose_page`",
)
CODED_FIGURE = "coded_figure"
PARITY = (
    "Ajrakh's kinds",
    "every chapter and every",
    "every component kind Ajrakh has",
    "the same kinds in the same",
)
NEXT_STEPS = {
    "get_page": "playbook/1",
    "get_facts": "playbook/1",
    "compose_component": "playbook/1",
    "edit_draft": "playbook/1",
    "preview_page": "playbook/1",
    "propose_page": "playbook/1",
    "list_components": "cookbook/1",
    "propose_structure": "compose_component",
}


def entries() -> dict[str, str]:
    return {match["kind"]: match["body"] for match in ENTRY.finditer(reference_text("cookbook"))}


def line(body: str, name: str) -> str:
    found = re.search(rf"^- \*\*{re.escape(name)}\*\*: (?P<text>.*?)(?=^- \*\*|\Z)", body, re.M | re.S)
    assert found is not None, name
    return " ".join(found["text"].split())


def registry_kinds() -> set[str]:
    return {
        *CONTRIBUTABLE_KINDS,
        *COMPONENT_KINDS,
        *PAGE_TOOL_KINDS,
        *AUTHORED_ART_KINDS,
        *AUTHORED_SCRIPT_KINDS,
        *DOCUMENT_KINDS,
        *DECLARED_ONLY_KINDS,
        *GENERAL_KINDS,
        *COMPOSED_KINDS,
    }


def uncovered(kinds: Iterable[str], written: Mapping[str, str]) -> set[str]:
    return set(kinds) - set(written)


def test_the_playbook_is_one_page_with_its_steps_in_order() -> None:
    playbook = reference_text("playbook")
    assert len(guide_sheets("playbook")) == 1
    steps = [(int(match["number"]), match["title"]) for match in STEP.finditer(playbook)]
    assert steps == list(enumerate(STEPS, start=1))
    places = [playbook.find(name) for name in TOOLS_IN_ORDER]
    assert -1 not in places and places == sorted(places)


def test_the_playbook_teaches_the_thinking_and_sets_no_page_to_copy_ajrakh() -> None:
    playbook = " ".join(reference_text("playbook").split())
    for said in (
        "KalaVigyan guarantees the research and the citations; you do the design and the build.",
        "free to design and code anything the page's cited facts support",
        "three.js interactives, d3 and canvas figures, short films, up to a whole chapter section",
        "Every fact a figure shows comes from the page's cited research.",
        "never a template",
        "never a target",
        "Take the reasoning, not the list.",
        "Never which kind, tool, layout, size or order: those are yours.",
        "never the person's problem",
    ):
        assert said in playbook, said
    for text in (playbook, SERVER_INSTRUCTIONS, bar_text(), ADD, PREVIEW, READ_NEXT, REVIEWED, SUBMITTED):
        for parity in PARITY:
            assert parity not in text, parity


@pytest.mark.parametrize("name", ["playbook", "cookbook"])
def test_every_guide_address_it_names_is_a_page_the_server_serves(name: str) -> None:
    named = {match["address"] for match in ADDRESS.finditer(reference_text(name))}
    assert named, name
    for address in named:
        assert guide_sheet(address).address == address


def test_the_playbook_names_the_design_system_the_worked_chapters_and_the_kit_before_building() -> None:
    playbook = reference_text("playbook")
    for address in ("kalavigyan-design/1", "system/1", "ajrakh-chemistry/1", "bar/1", "cookbook/1"):
        assert 0 <= playbook.find(f"`{address}`") < playbook.find("## The making"), address
    for address in ("kit-stylesheet/1", "kit-script/1", "sources/1", "quotes/1", "datasets/1"):
        assert f"`{address}`" in playbook, address


def test_the_cookbook_has_an_entry_for_every_kind_the_registry_knows_and_a_new_kind_fails() -> None:
    written = entries()
    assert uncovered(registry_kinds(), written) == set()
    assert uncovered({*registry_kinds(), "a_new_kind"}, written) == {"a_new_kind"}
    assert set(written) - registry_kinds() <= {CODED_FIGURE}


def test_each_entry_holds_its_seven_lines_and_the_group_table_names_only_entries() -> None:
    written = entries()
    for kind, body in written.items():
        for name in LINES:
            assert line(body, name), (kind, name)
    table = reference_text("cookbook").split("## Reading an entry")[0]
    assert set(re.findall(r"`([a-z0-9_]+)`", table.split("| Group | Kinds |")[1])) == set(written)


def test_every_kutch_ajrakh_component_is_named_in_its_kind_s_entry_with_its_worked_chapter() -> None:
    written = entries()
    page = worked_page()
    kinds = {component.label: component.kind for component in page.content.components}
    for component in page.content.components:
        shown = line(written[component.kind], "In Kutch Ajrakh")
        assert f"`{component.label}`" in shown, component.label
        assert f"`{worked_topic(component.chapter)}/1`" in shown, component.label
    for kind, body in written.items():
        for match in LABEL.finditer(line(body, "In Kutch Ajrakh")):
            assert kinds.get(match["label"]) == kind, (kind, match["label"])


def test_every_kind_the_server_composes_names_compose_component_as_a_way_to_make_it() -> None:
    written = entries()
    for kind in COMPOSED_KINDS:
        assert "`compose_component`" in line(written[kind], "Made by"), kind
    assert "`coded_figure`" in line(written["reaction_player"], "Made by")


def test_each_worked_chapter_holds_every_component_of_its_chapter_with_its_spec() -> None:
    page = worked_page()
    for chapter in page.chapters():
        text = worked_text(chapter.key)
        assert text.startswith(f"# Kutch Ajrakh, worked: {chapter.title}\n\n"), chapter.key
        assert "never as a template" in text
        for component in page.components(chapter.key):
            section = text.split(f"\n## `{component.label}`\n", 1)
            assert len(section) == 2, component.label
            body = section[1].split("\n## ", 1)[0]
            assert f"Kind `{component.kind}`" in body and "Where it sits:" in body
            assert ("```json" in body) == (component.label in page.specs), component.label
        assert GUIDES[worked_topic(chapter.key)].text() == text


def test_a_spec_keeps_its_shape_and_cuts_long_texts_lists_and_drawings() -> None:
    drawing = {
        "tag": "svg",
        "children": [{"tag": "g", "children": [{"tag": "path", "children": [{"tag": "title"}]}]}],
    }
    spec = {"title": "u0001", "steps": [1, 2, 3, 4, 5], "note": "x" * 200, "drawing": drawing}
    assert trimmed_spec(spec) == {
        "title": "u0001",
        "steps": [1, 2, 3, f"{CUT} and 2 more"],
        "note": "x" * 160 + CUT,
        "drawing": {
            "tag": "svg",
            "children": [{"tag": "g", "children": [{"tag": "path", "children": f"{CUT} 1 drawing nodes"}]}],
        },
    }
    assert trimmed_spec({"steps": [1, 2, 3]}) == {"steps": [1, 2, 3]}


@pytest.mark.parametrize("topic", sorted(KIT_GUIDES))
def test_each_kit_guide_holds_its_kit_file_whole_in_one_fence(topic: str) -> None:
    guide = KIT_GUIDES[topic]
    text = GUIDES[topic].text()
    source = kit_sources()[guide.file]
    assert text.startswith(f"# {guide.title}\n\n") and f"\n## {guide.file}\n\n```{guide.language}\n" in text
    assert source in text and text.endswith("```\n") and text.count("\n```") == 2
    assert "".join(sheet.text for sheet in guide_sheets(topic)) == text


def test_the_design_skill_is_one_text_in_the_repository_on_the_server_and_on_the_site() -> None:
    files = [file for file in SKILL_FILES.values() if file.skill == DESIGN_SKILL]
    assert sorted(file.name for file in files) == ["SKILL.md", "references/SYSTEM.md"]
    for file in files:
        source = (CLAUDE_SKILLS / file.skill / file.name).read_bytes()
        assert file.path.read_bytes() == source, file.name
        assert (SITE_SKILLS / file.skill / file.name).read_bytes() == source, file.name
        assert skill_file_text(file.uri) == source.decode("utf-8")
    assert guide_sheets("kalavigyan-design")[0].title == "KalaVigyan design system"
    assert guide_sheets("system")[0].title == "KalaVigyan design system"


@pytest.mark.parametrize("name", sorted(NEXT_STEPS))
def test_every_page_building_tool_s_description_says_where_it_sits_in_the_playbook(name: str) -> None:
    assert NEXT_STEPS[name] in TOOLS[name].description, name
