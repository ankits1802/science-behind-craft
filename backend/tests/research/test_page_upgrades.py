from datetime import UTC, datetime
from typing import Any

from app.research.monograph_document import MonographDocument
from app.research.open_work import TASK_KINDS, TASK_PROMPTS, SubjectStanding, TaskSubject, parse_task_key
from app.research.open_work_tasks import subject_tasks
from app.research.page_report_drawable import HeldChange, HeldShapes
from app.research.page_upgrades import UPGRADE_CUTOFF, upgrade_lines
from app.services.nightly_upkeep import UpkeepReport
from app.services.open_work import SUBJECT_TARGETS

from .page_report_rules_fixtures import SLUG, page_document, sentence

MAP = "test-craft/geography/the-town"
TOWN = {"geography-1": sentence("GEOGRAPHY", "The town lies on a plain south of the city.", "c33")}
STAGES = HeldShapes(stages=(HeldChange("S01", "Harda", ("c21",)), HeldChange("S02", "Syahi", ("c22",))))
STAGE_LINE = (
    "made: 2 stages in order (Harda, Syahi) with no player stepping through them, stated by c21, c22; "
    "draw it as a stage_player you write, each stage a kit scene of what its facts name if it serves the reader"
)
NO_MAP_LINE = (
    "why: 1 sentence of places, stated by c33, and no places map; a map_layer declared from them is drawn on "
    "the site's own base, framed to its places with relief, rivers, district lines and the India locator, and "
    "may name a frame, layers to emphasise, routes, rings, district values or a sequence, each cited "
    "(decision 0232)"
)
BARE_MAP_LINE = (
    f"why: the places map {MAP} is drawn on the site's own base now but says only where its places are; it "
    "could say what it is about with a frame, layers to emphasise, routes, rings, district values or a "
    "sequence the facts state, each cited (decision 0232)"
)
LETTERS = "-abcdefgh"
PLAYBOOK = "the page playbook (kalavigyan://skills/references/playbook.md, guide page playbook/1)"


def making(count: int) -> dict[str, dict[str, Any]]:
    return {
        f"making-{n}": sentence("PROCESS", f"The printer presses block {LETTERS[n]} by hand.", f"c5{n}")
        for n in range(1, count + 1)
    }


def prose_line(chapter: str, count: int, facts: str) -> str:
    return (
        f"{chapter}: {count} cited paragraphs run on with no figure, stated by {facts}; Kutch Ajrakh draws a "
        "figure in every chapter of cited prose, so a figure could carry what they state, among them a "
        "coded_figure written over the chapter's cited data (decision 0231)"
    )


def with_map(document: MonographDocument, spec: dict[str, Any]) -> MonographDocument:
    body = document.model_dump(mode="json", by_alias=True)
    body["content"]["components"].append(
        {
            "label": MAP,
            "chapter": "why",
            "anchor": "#" + MAP.replace("/", "--"),
            "kind": "map_layer",
            "title": "The town and its neighbours",
            "description": "The town and its neighbours, drawn for the test.",
            "field": "GEOGRAPHY",
            "fields": [],
            "subjects": [],
        }
    )
    body["content"]["layout"].append({"chapter": "why", "kind": "component", "ref": MAP, "within": None})
    body["specs"][MAP] = spec
    return MonographDocument.model_validate(body)


def standing(upgrade: tuple[str, ...] | None) -> SubjectStanding:
    subject = TaskSubject(
        kind="craft", slug=SLUG, name="Test craft", page_url=f"https://kalavigyan.example/crafts/{SLUG}"
    )
    return SubjectStanding(subject=subject, targets=SUBJECT_TARGETS["craft"], upgrade=upgrade)


def test_the_round_reached_the_site_when_main_took_its_first_release() -> None:
    assert datetime(2026, 11, 26, 5, 51, tzinfo=UTC) == UPGRADE_CUTOFF


def test_a_page_whose_facts_wait_for_nothing_new_is_named_nothing() -> None:
    assert upgrade_lines(page_document(), None) == []


def test_rule_29_s_opportunities_are_named_as_the_preview_names_them() -> None:
    assert upgrade_lines(page_document(), STAGES) == [STAGE_LINE]


def test_places_with_no_places_map_ask_for_one_on_the_site_s_base() -> None:
    assert upgrade_lines(page_document(extra=TOWN), None) == [NO_MAP_LINE]


def test_a_places_map_that_says_only_where_asks_what_it_is_about_and_one_with_a_frame_does_not() -> None:
    bare = with_map(page_document(extra=TOWN), {"head": {"title": "u-map"}, "places": [{"name": "Town"}]})
    assert upgrade_lines(bare, None) == [BARE_MAP_LINE]
    framed = with_map(page_document(extra=TOWN), {"head": {"title": "u-map"}, "frame": {"state": 8}})
    assert upgrade_lines(framed, None) == []


def test_a_chapter_of_three_cited_paragraphs_and_no_figure_asks_for_a_figure_and_two_do_not() -> None:
    assert upgrade_lines(page_document(extra=making(3)), None) == [prose_line("made", 3, "c51, c52, c53")]
    assert upgrade_lines(page_document(extra=making(2)), None) == []
    long = "c51, c52, c53, c54, c55, c56 and 1 more"
    assert upgrade_lines(page_document(extra=making(7)), None) == [prose_line("made", 7, long)]


def test_a_chapter_already_named_is_not_named_twice() -> None:
    assert upgrade_lines(page_document(extra=making(3)), STAGES) == [STAGE_LINE]
    places = {
        f"geography-{n}": sentence("GEOGRAPHY", f"Village {LETTERS[n]} lies by the river.", f"c3{n}")
        for n in (1, 2, 3)
    }
    (line,) = upgrade_lines(page_document(extra=places), None)
    assert line.startswith("why: 3 sentences of places, stated by c31, c32, c33, and no places map;")


def test_a_raised_page_is_one_task_naming_its_lines_and_the_playbook_beside_the_page_tasks() -> None:
    tasks = subject_tasks(standing((STAGE_LINE,)))
    kinds = [task.kind for task in tasks]
    assert kinds.index("UPGRADE_PAGE") == kinds.index("PAGE_FORM") + 1
    (task,) = [task for task in tasks if task.kind == "UPGRADE_PAGE"]
    assert (task.key, task.priority, task.prompt, task.count) == (
        f"UPGRADE_PAGE:craft:{SLUG}",
        "LOW",
        "deliver_page",
        1,
    )
    assert task.needed == (
        "Test craft's page was built before the site drew what its facts now allow, and nobody has rebuilt it. "
        f"What its facts could now show: {STAGE_LINE}. Rebuild it by {PLAYBOOK}."
    )
    assert "preview_page" in task.acceptance and "propose_page" in task.acceptance


def test_no_task_without_a_raised_page_and_a_page_with_nothing_named_is_read_against_the_critique() -> None:
    assert "UPGRADE_PAGE" not in [task.kind for task in subject_tasks(standing(None))]
    (task,) = [task for task in subject_tasks(standing(())) if task.kind == "UPGRADE_PAGE"]
    assert task.count == 0
    assert "against the design critique (design-critique/1)" in task.needed


def test_the_kind_is_a_page_task_delivered_as_a_page_and_its_key_parses() -> None:
    assert TASK_KINDS.index("UPGRADE_PAGE") == TASK_KINDS.index("PAGE_LAYOUT") + 1
    assert TASK_PROMPTS["UPGRADE_PAGE"] == "deliver_page"
    parsed = parse_task_key("UPGRADE_PAGE:family:Some-Family")
    assert (parsed.kind, parsed.subject_kind, parsed.slug, parsed.detail) == (
        "UPGRADE_PAGE",
        "family",
        "Some-Family",
        None,
    )


def test_the_night_reports_what_it_raised() -> None:
    assert UpkeepReport().as_dict()["pageUpgrades"] == {
        "raised": [],
        "alreadyRaised": 0,
        "noDocument": [],
        "failed": {},
    }
