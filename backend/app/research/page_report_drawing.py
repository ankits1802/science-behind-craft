from __future__ import annotations

from collections import Counter

from .page_render import (
    CHECKED,
    FAILED,
    PAGE_LABEL,
    UNMADE,
    WIDTHS,
    DrawingReport,
    DrawnImage,
    DrawnProblem,
    RenderResult,
    RenderUnmade,
    image_bytes,
    kept_images,
)
from .page_report import READY, PageReport, RuleCheck
from .page_report_rules import EVIDENCE_MAX, FAIL, JUDGE, PASS, Verdict

__all__ = ["DRAWING_RULE", "drawing_report", "problem_line", "with_drawing"]

DRAWING_RULE = 28
CHECKED_LINE = (
    "drawn at {widths} px wide in light and checked as the release checks a live page: the first screen, "
    "every component and the page's width pass"
)
UNMADE_LINE = (
    "the pictures could not be made: {message} The drawing checks did not run, so nothing here says the page "
    "draws well; read it on the private link at 390 and 1440 px."
)
WHOLE_PAGE = "the page"


def drawing_report(outcome: RenderResult | RenderUnmade) -> DrawingReport:
    if isinstance(outcome, RenderUnmade):
        return DrawingReport(state=UNMADE, widths=[], problems=[], images=[], reason=outcome.message)
    images = [
        DrawnImage(
            name=image.name,
            caption=image.caption,
            width=image.width,
            height=image.height,
            bytes=image_bytes(image),
        )
        for image in kept_images(outcome.images)
    ]
    return DrawingReport(
        state=FAILED if outcome.problems else CHECKED,
        widths=list(WIDTHS),
        problems=outcome.problems,
        images=images,
        blocked=outcome.blocked,
    )


def problem_line(problem: DrawnProblem) -> str:
    label = WHOLE_PAGE if problem.label == PAGE_LABEL else problem.label
    return f"{problem.width} px, {label}: {problem.problem}"


def with_drawing(report: PageReport, drawing: DrawingReport) -> PageReport:
    verdict, evidence = _verdict(drawing)
    rules = [
        RuleCheck(rule=check.rule, title=check.title, verdict=verdict, evidence=evidence)
        if check.rule == DRAWING_RULE
        else check
        for check in report.rules
    ]
    counted = Counter(check.verdict for check in rules)
    return report.model_copy(
        update={
            "rules": rules,
            "passed": counted[PASS],
            "failed": counted[FAIL],
            "judged": counted[JUDGE],
            "message": READY.format(passed=counted[PASS], failed=counted[FAIL], judged=counted[JUDGE]),
            "drawing": drawing,
        }
    )


def _verdict(drawing: DrawingReport) -> Verdict:
    if drawing.state == UNMADE:
        return JUDGE, [UNMADE_LINE.format(message=drawing.reason or "the renderer gave no reason.")]
    if drawing.state == FAILED:
        return FAIL, [problem_line(problem) for problem in drawing.problems][:EVIDENCE_MAX]
    return PASS, [CHECKED_LINE.format(widths=" and ".join(str(width) for width in drawing.widths))]
