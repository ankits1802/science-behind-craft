import base64

from app.research.page_render import DrawnProblem, RenderedImage, RenderResult, RenderUnmade
from app.research.page_report import PageReport, ReportInput, page_report
from app.research.page_report_drawing import DRAWING_RULE, drawing_report, problem_line, with_drawing
from app.services.page_report import checklist_titles

from .page_report_rules_fixtures import FIGURE, page_document

ICON = DrawnProblem(width=390, label=FIGURE, problem="an icon of 24 units draws 239px wide")
WIDE = DrawnProblem(
    width=390, label="page", problem="is 310px wider than the 390px screen, so it scrolls sideways"
)
NOT_RUNNING = "the renderer is not running on the API's box just now."


def base() -> PageReport:
    return page_report(ReportInput(document=page_document()), checklist_titles())


def drawn(*problems: DrawnProblem, images: list[RenderedImage] | None = None) -> RenderResult:
    return RenderResult(problems=list(problems), images=images or [], seconds=12.5)


def rule(report: PageReport) -> tuple[str, list[str]]:
    (found,) = [check for check in report.rules if check.rule == DRAWING_RULE]
    return found.verdict, found.evidence


def test_before_the_page_is_drawn_rule_28_is_left_to_judge() -> None:
    report = base()
    verdict, evidence = rule(report)
    assert verdict == "JUDGE" and "390 and 1440 px" in evidence[0]
    assert report.drawing is None


def test_a_drawing_problem_fails_rule_28_with_the_component_and_the_problem_in_words() -> None:
    before = base()
    after = with_drawing(before, drawing_report(drawn(ICON, WIDE)))
    assert rule(after) == (
        "FAIL",
        [
            f"390 px, {FIGURE}: an icon of 24 units draws 239px wide",
            "390 px, the page: is 310px wider than the 390px screen, so it scrolls sideways",
        ],
    )
    assert (after.passed, after.failed, after.judged) == (before.passed, before.failed + 1, before.judged - 1)
    assert after.message.startswith(f"{after.passed} rules pass, {after.failed} fail")
    assert after.drawing is not None and after.drawing.state == "FAILED"


def test_a_page_drawn_whole_passes_rule_28() -> None:
    before = base()
    after = with_drawing(before, drawing_report(drawn()))
    verdict, evidence = rule(after)
    assert verdict == "PASS" and "drawn at 390 and 1440 px wide" in evidence[0]
    assert (after.passed, after.judged) == (before.passed + 1, before.judged - 1)


def test_pictures_that_could_not_be_made_never_pass_and_say_why() -> None:
    before = base()
    after = with_drawing(before, drawing_report(RenderUnmade(reason="UNREACHABLE", message=NOT_RUNNING)))
    verdict, evidence = rule(after)
    assert verdict == "JUDGE"
    assert evidence[0].startswith(f"the pictures could not be made: {NOT_RUNNING}")
    assert "nothing here says the page draws well" in evidence[0]
    assert (after.passed, after.failed, after.judged) == (before.passed, before.failed, before.judged)
    assert after.drawing is not None and (after.drawing.state, after.drawing.images) == ("UNMADE", [])


def test_a_long_list_of_problems_is_cut_to_twelve_lines_and_kept_whole_in_the_drawing() -> None:
    many = [DrawnProblem(width=1440, label=f"{FIGURE}-{n}", problem="draws empty") for n in range(15)]
    after = with_drawing(base(), drawing_report(drawn(*many)))
    assert len(rule(after)[1]) == 12
    assert after.drawing is not None and len(after.drawing.problems) == 15


def test_the_drawing_lists_the_pictures_kept_with_their_size() -> None:
    data = base64.b64encode(b"y" * 2048).decode("ascii")
    shot = RenderedImage(
        name="first-screen-390", caption="The first screen", width=390, height=844, data=data
    )
    drawing = drawing_report(drawn(images=[shot]))
    assert [(found.name, found.width, found.height, found.bytes) for found in drawing.images] == [
        ("first-screen-390", 390, 844, 2048)
    ]
    assert drawing.widths == [390, 1440]


def test_a_problem_of_the_whole_page_is_said_as_the_page() -> None:
    assert problem_line(WIDE).startswith("390 px, the page: ")
    assert problem_line(ICON) == f"390 px, {FIGURE}: an icon of 24 units draws 239px wide"
