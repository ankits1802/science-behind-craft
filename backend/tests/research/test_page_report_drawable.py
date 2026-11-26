from typing import Any

from app.research.monograph_document import MonographDocument
from app.research.page_report import ReportInput, page_report
from app.research.page_report_drawable import DRAWABLE_RULE, HeldChange, HeldShapes
from app.research.page_report_rules import checked_rules

from .page_report_rules_fixtures import page_document, sentence

IRON = HeldChange("R04", "iron and acetic acid to iron(II) acetate and hydrogen", ("c9",))
STAGES = (
    HeldChange("S01", "Harda", ("c21",)),
    HeldChange("S02", "Syahi", ("c22",)),
    HeldChange("S03", "Black printing", ("c23",)),
)
WRITTEN_REACTION = "a reaction_player or equation_card you write, its scenes drawn from the figure kit"
WRITTEN_STAGES = "a stage_player you write, each stage a kit scene of what its facts name"
DATED = {
    "history-1": sentence("HISTORY", "Printers came to the town in 1790.", "c31"),
    "history-2": sentence("HISTORY", "The print was registered as a GI in 2009.", "c32"),
    "geography-1": sentence("GEOGRAPHY", "The town lies on a plain south of the city.", "c33"),
}
MEASURED = {
    "economics-1": sentence("ECONOMICS", "Printing one sari takes 6 hours.", "c41"),
    "economics-2": sentence("ECONOMICS", "Women make up 40 % of the printers.", "c42"),
}


def with_figure(
    document: MonographDocument, label: str, kind: str, field: str, *claims: str
) -> MonographDocument:
    body = document.model_dump(mode="json", by_alias=True)
    content = body["content"]
    ref = f"u7{len(content['components']):03d}"
    content["units"][ref] = {
        "chapter": "chem",
        "tag": "span",
        "field": field,
        "nodes": ["x"],
        "claimIds": list(claims),
    }
    content["layout"] += [
        {"chapter": "chem", "kind": "component", "ref": label, "within": None},
        {"chapter": "chem", "kind": "unit", "ref": ref, "within": label},
    ]
    content["components"].append(
        {
            "label": label,
            "chapter": "chem",
            "anchor": "#" + label.replace("/", "--"),
            "kind": kind,
            "title": "A figure for the test",
            "description": "A figure drawn for the test.",
            "field": field,
            "fields": [],
            "subjects": [],
        }
    )
    return MonographDocument.model_validate(body)


def judged(document: MonographDocument, held: HeldShapes | None = None) -> tuple[str, list[str]]:
    return checked_rules(ReportInput(document=document, held=held))[DRAWABLE_RULE]


def test_a_balanced_reaction_no_figure_draws_is_an_opportunity_yours_to_judge_never_a_failure() -> None:
    verdict, evidence = judged(page_document(), HeldShapes(reactions=(IRON,), composers=("reaction_player",)))
    assert (verdict, evidence) == (
        "JUDGE",
        [
            f"chem: the reaction R04, {IRON.said}, balanced and drawn nowhere, stated by c9; draw it as "
            f"{WRITTEN_REACTION} or compose_component with kind reaction_player, as a shortcut if it serves "
            "the reader"
        ],
    )


def test_a_figure_you_write_citing_the_reaction_draws_it_and_a_table_of_it_does_not() -> None:
    held = HeldShapes(reactions=(IRON,))
    tabled = with_figure(page_document(), "test-craft/chemistry/iron-table", "fact_table", "CHEMISTRY", "c9")
    assert judged(tabled, held)[0] == "JUDGE"
    drawn = with_figure(tabled, "test-craft/chemistry/iron-drawing", "drawing", "CHEMISTRY", "c9")
    assert judged(drawn, held) == (
        "PASS",
        ["nothing this craft's facts state waits for a figure the page does not draw"],
    )


def test_without_a_composer_for_its_kind_the_way_on_is_the_figure_you_write() -> None:
    report = page_report(ReportInput(document=page_document(), held=HeldShapes(reactions=(IRON,))), {})
    (opportunity,) = report.opportunities
    assert (opportunity.shows, opportunity.chapter, opportunity.facts) == ("REACTION", "chem", ["c9"])
    assert opportunity.ways == [WRITTEN_REACTION]


def test_stages_in_order_with_no_player_are_an_opportunity_until_a_player_steps_through_them() -> None:
    held = HeldShapes(stages=STAGES, composers=("dip_player", "molecule_3d"))
    report = page_report(ReportInput(document=page_document(), held=held), {})
    (opportunity,) = report.opportunities
    assert (
        opportunity.what
        == "3 stages in order (Harda, Syahi, Black printing) with no player stepping through them"
    )
    assert (opportunity.chapter, opportunity.facts) == ("made", ["c21", "c22", "c23"])
    assert opportunity.ways == [WRITTEN_STAGES, "compose_component with kind dip_player, as a shortcut"]
    played = with_figure(page_document(), "test-craft/process/every-stage", "stage_player", "PROCESS", "c22")
    assert judged(played, held)[0] == "PASS"


def test_places_and_dates_with_no_map_moving_through_them_are_an_opportunity() -> None:
    dated = page_document(extra=DATED)
    report = page_report(ReportInput(document=dated), {})
    (opportunity,) = report.opportunities
    assert (opportunity.shows, opportunity.chapter, opportunity.facts) == (
        "PLACES_AND_DATES",
        "history",
        ["c31", "c32"],
    )
    mapped = with_figure(dated, "test-craft/geography/the-town", "map_layer", "GEOGRAPHY", "c33")
    assert judged(mapped)[0] == "JUDGE"
    moving = with_figure(dated, "test-craft/history/the-town-through-time", "timeline_map", "HISTORY", "c31")
    assert judged(moving)[0] == "PASS"


def test_quantities_a_field_states_with_no_figure_of_that_field_are_an_opportunity() -> None:
    measured = page_document(extra=MEASURED)
    report = page_report(ReportInput(document=measured), {})
    (opportunity,) = report.opportunities
    assert opportunity.what == "2 quantities with units stated in economics with no figure of that field"
    assert (opportunity.chapter, opportunity.facts) == ("market", ["c41", "c42"])
    charted = with_figure(measured, "test-craft/economics/hours-and-hands", "chart", "ECONOMICS", "c41")
    assert judged(charted)[0] == "PASS"


def test_a_page_with_nothing_waiting_passes_and_rule_29_never_fails_a_page() -> None:
    every: list[Any] = [
        judged(page_document()),
        judged(page_document(extra={**DATED, **MEASURED}), HeldShapes(reactions=(IRON,), stages=STAGES)),
    ]
    assert every[0][0] == "PASS"
    assert every[1][0] == "JUDGE" and len(every[1][1]) == 4
