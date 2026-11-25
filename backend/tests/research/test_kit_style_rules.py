import re
from pathlib import Path

import pytest

from app.scripts.build_monograph import PUBLIC_KIT_DIR
from app.services.document_kit_defs import KIT_STYLE_FILE
from app.services.monograph_document import KIT_DIR

RULE = re.compile(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}")
EQUATION_LABEL = ".bx-{scope} .eq .sp small"
SCOPES_DRAWING_EQUATIONS = ("chem", "mb", "pt", "rm")


def declarations(css: str, selector: str) -> str:
    return " ".join(
        rule.group("body") for rule in RULE.finditer(css) if rule.group("selector").strip() == selector
    )


@pytest.mark.parametrize("folder", [KIT_DIR, PUBLIC_KIT_DIR], ids=["source", "served"])
@pytest.mark.parametrize("scope", SCOPES_DRAWING_EQUATIONS)
def test_an_equation_label_wraps_inside_its_box_in_every_scope_that_draws_equations(
    folder: Path, scope: str
) -> None:
    css = (folder / KIT_STYLE_FILE).read_bytes().decode("utf-8")
    held = declarations(css, EQUATION_LABEL.format(scope=scope))
    assert "max-width: 15ch" in held
    assert "white-space: normal" in held


LANE_WORDS = (
    ".bx-chem .lane .spc .nm",
    ".bx-chem .lane .spc .fm",
    ".bx-chem .lane .spc .st",
    ".bx-chem .lane .arr small",
)
LANE_HOLDERS = (
    ".bx-chem .rp-chems, .bx-chem .rp-chem, .bx-chem .lane, .bx-chem .lane .spc, .bx-chem .lane .spc > span, "
    ".bx-chem .lane .arr"
)
SCROLLS = re.compile(r"overflow(-x|-y)?:\s*(auto|scroll)")


@pytest.mark.parametrize("folder", [KIT_DIR, PUBLIC_KIT_DIR], ids=["source", "served"])
@pytest.mark.parametrize("selector", LANE_WORDS)
def test_a_species_name_formula_state_and_change_wrap_inside_the_lane(folder: Path, selector: str) -> None:
    css = (folder / KIT_STYLE_FILE).read_bytes().decode("utf-8")
    held = declarations(css, selector)
    assert "overflow-wrap: anywhere" in held
    assert "min-width: 0" in held
    assert "nowrap" not in held


@pytest.mark.parametrize("folder", [KIT_DIR, PUBLIC_KIT_DIR], ids=["source", "served"])
def test_no_part_of_a_player_s_lane_or_its_ribbon_shows_a_scroll_bar(folder: Path) -> None:
    css = (folder / KIT_STYLE_FILE).read_bytes().decode("utf-8")
    lane = [rule for rule in RULE.finditer(css) if ".lane" in rule.group("selector")]
    assert len(lane) > 10
    assert not [rule.group("selector") for rule in lane if SCROLLS.search(rule.group("body"))]
    assert "overflow: visible" in declarations(css, LANE_HOLDERS)
    assert "scrollbar-width: none" in declarations(css, ".bx-pt .lc-ribbon")
    assert "scrollbar-width: thin" not in declarations(css, ".bx-pt .lc-ribbon")
