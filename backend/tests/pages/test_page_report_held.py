from typing import Any

from app.research.page_report import ReportInput, page_report
from app.research.page_report_drawable import HeldChange
from app.services.compose_components import COMPOSED_KINDS, ComposeDeps
from app.services.compose_held import CraftHeld
from app.services.page_report_held import held_shapes, shapes_of

from ..compose.held import BAGRU, SLUG, claim
from ..research.page_report_rules_fixtures import page_document

NO_SESSION: Any = None
SYAHI = str(claim(2))


def deps(craft: CraftHeld | None) -> ComposeDeps:
    async def read(_session: Any, slug: str) -> CraftHeld | None:
        assert slug == SLUG
        return craft

    return ComposeDeps(held=read)


def test_only_the_reactions_the_server_balanced_and_the_stages_facts_state_are_offered() -> None:
    shapes = shapes_of(BAGRU)
    assert shapes.reactions == (
        HeldChange("R04", "iron and acetic acid to iron(II) acetate and hydrogen", (SYAHI,)),
    )
    assert [stage.key for stage in shapes.stages] == ["S01", "S02", "S03", "S04", "S05"]
    assert shapes.stages[1] == HeldChange("S02", "Syahi", (SYAHI,))
    assert shapes.composers == COMPOSED_KINDS


async def test_a_craft_s_page_reads_its_held_shapes_and_another_subject_or_an_uncurated_craft_none() -> None:
    assert await held_shapes(NO_SESSION, deps(BAGRU), "craft", SLUG) == shapes_of(BAGRU)
    assert await held_shapes(NO_SESSION, deps(None), "craft", SLUG) is None
    assert await held_shapes(NO_SESSION, deps(BAGRU), "category", SLUG) is None


def test_the_craft_s_facts_become_opportunities_with_the_composers_of_the_registry_as_shortcuts() -> None:
    report = page_report(ReportInput(document=page_document(), held=shapes_of(BAGRU)), {})
    reaction, stages = report.opportunities
    assert (reaction.shows, reaction.facts) == ("REACTION", [SYAHI])
    assert reaction.ways[1] == "compose_component with kind reaction_player, as a shortcut"
    assert stages.shows == "STAGES" and stages.what.startswith(
        "5 stages in order (Harda, Syahi, Black printing,"
    )
    assert stages.ways[1:] == ["compose_component with kind dip_player, as a shortcut"]
    assert [check.verdict for check in report.rules if check.rule == 29] == ["JUDGE"]
