import pytest

from app.research.sandbox import sandbox_problems
from app.research.simulation_art import ART_RULE, simulation_art_problems

from ..contracts.golden import golden_json
from ..simulations.at_the_bar import IRON_AT_THE_BAR, KUT_AT_THE_BAR, WATER_AT_THE_BAR

RECORDED = ("explainer.craft-mechanism.golden.json", "explainer.simulation-mechanism.golden.json")
BELOW = (
    '<svg viewBox="0 0 320 120"><rect x="8" y="8" width="304" height="40" fill="var(--chart-series)"></rect>'
    '<circle cx="160" cy="80" r="12" fill="var(--chart-emph)"></circle></svg>'
)
AT = (
    '<svg viewBox="0 0 320 120" role="img" aria-label="Fall of the level year by year">'
    '<rect x="0" y="0" width="320" height="120" fill="var(--sunk)"></rect>'
    '<line x1="16" y1="100" x2="304" y2="100" stroke="var(--ink-1)"></line>'
    '<rect x="32" y="60" width="40" height="40" fill="var(--chart-series)" stroke="var(--ink-1)"></rect>'
    '<rect x="96" y="40" width="40" height="60" fill="var(--chart-series)" stroke="var(--ink-1)"></rect>'
    '<rect x="160" y="20" width="40" height="80" fill="var(--chart-emph)" stroke="var(--ink-1)"></rect>'
    '<line x1="16" y1="20" x2="16" y2="100" stroke="var(--ink-3)"></line>'
    '<text x="32" y="116" font-size="12" fill="var(--ink-2)">Year</text></svg>'
)


def details(html: str) -> list[str]:
    found = simulation_art_problems(html)
    assert {problem.rule for problem in found} <= {ART_RULE}
    return [problem.detail for problem in found]


def recorded_html(name: str) -> str:
    return golden_json(name)["block"]["html"]


@pytest.mark.parametrize("html", [WATER_AT_THE_BAR, IRON_AT_THE_BAR, KUT_AT_THE_BAR, AT])
def test_a_fragment_drawn_in_the_design_is_at_the_bar(html: str) -> None:
    assert details(html) == []


@pytest.mark.parametrize("html", [WATER_AT_THE_BAR, KUT_AT_THE_BAR])
def test_the_fragments_at_the_bar_still_pass_the_sandbox(html: str) -> None:
    assert sandbox_problems(html, {"fallLowFeet": 10.0, "fallHighFeet": 15.0}) == []


def test_the_recorded_kut_explainer_falls_below_the_bar_on_every_count() -> None:
    found = details(recorded_html(RECORDED[0]))
    colours = [detail.split("'")[1] for detail in found if detail.startswith("names the colour")]
    assert colours == ["#1d1b16", "#faf7f0", "#c9bfa8", "#fff", "#d8c9a3", "#3b2a20"]
    assert any(detail.startswith("sets text at '15px', off the type scale") for detail in found)
    assert any(detail.startswith("sets text in 'system-ui,sans-serif'") for detail in found)
    assert any(detail.startswith("rests at opacity .4") for detail in found)
    assert any(detail.startswith("times its motion without reading") for detail in found)
    assert any("said to show cloth ('A strip of harde-treated cloth')" in detail for detail in found)
    assert len(found) == 11


def test_the_recorded_iron_explainer_falls_below_the_bar_without_painting_a_material() -> None:
    found = details(recorded_html(RECORDED[1]))
    colours = [detail.split("'")[1] for detail in found if detail.startswith("names the colour")]
    assert colours == ["#1d1b16", "#faf7f0", "#c9bfa8", "#fff"]
    assert not any("said to show" in detail or "by hand" in detail for detail in found)
    assert len(found) == 8


def test_a_drawing_of_too_few_shapes_and_no_ink_is_held_to_the_scene_bar() -> None:
    found = details(BELOW)
    assert any("figure[0] draws 2 shapes, fewer than the 6" in detail for detail in found)
    assert any("figure[0] has no line work in ink" in detail for detail in found)


@pytest.mark.parametrize(
    ("html", "said"),
    [
        ("<style>.a{background:var(--dye-kut)}</style>", "paints --dye-kut by hand"),
        ('<svg viewBox="0 0 10 10"><path d="M0 0" fill="var(--indigo)"></path></svg>', "--indigo is indigo"),
        ("<style>.a{color:var(--brand)}</style>", "--brand is not one of the design's roles"),
        ("<style>.a{border:1px solid black}</style>", "names the colour 'black'"),
        ("<style>.a{font-size:1rem}</style>", "sets text at '1rem', off the type scale"),
        ("<style>.a{font-family:Georgia}</style>", "sets text in 'Georgia'"),
        ("<style>.a{opacity:40%}</style>", "rests at opacity 40%"),
        ("<script>setTimeout(go, 1000);</script>", "times its motion without reading"),
        ("<script>a.setAttribute('fill', '#2f5d8a');</script>", "the script paints '#2f5d8a'"),
        ('<div role="img" aria-label="The vat at rest"></div>', "said to show vat"),
    ],
)
def test_each_rule_of_the_bar_refuses_its_own_fault(html: str, said: str) -> None:
    assert any(said in detail for detail in details(html))


OWN_FLAG = (
    "<script>const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;\n"
    "if (!reducedMotion) timer = setInterval(step, 1000);</script>"
)


@pytest.mark.parametrize(
    ("html", "said"),
    [
        (OWN_FLAG, "times its motion without reading"),
        (
            '<svg viewBox="0 0 10 10"><rect width="4" height="4" fill="var(--sunk)">'
            '<animate attributeName="fill" values="var(--sunk);var(--raised)" dur="2s" repeatCount="indefinite">'
            "</animate></rect></svg>",
            "moves by <animate>, which neither reduced-motion switch stops",
        ),
        ('<svg viewBox="0 0 10 10"><set attributeName="x" to="4"></set></svg>', "moves by <set>"),
        (
            "<script>shown.animate([{opacity: 0}, {opacity: 1}], {iterations: Infinity});</script>",
            "moves by the Web Animations API (.animate(), which neither reduced-motion switch stops",
        ),
        ("<script>new KeyframeEffect(shown, [], 1000);</script>", "moves by the Web Animations API"),
    ],
)
def test_motion_neither_switch_stops_and_a_timer_that_reads_no_frame_flag_are_refused(
    html: str, said: str
) -> None:
    assert any(said in detail for detail in details(html))


@pytest.mark.parametrize(
    "script",
    [
        'const still = document.documentElement.getAttribute("data-reduced-motion") === "true";',
        'const still = document.documentElement.dataset["reducedMotion"] === "true";',
    ],
)
def test_a_timer_that_reads_the_frame_s_own_flag_either_way_passes(script: str) -> None:
    assert details(f"<script>{script}\nif (!still) timer = setInterval(step, 1000);</script>") == []


@pytest.mark.parametrize(
    ("html", "said"),
    [
        ('<canvas width="320" height="200"></canvas>', "draws on a <canvas>, which the bar cannot read"),
        (
            '<script>const ctx = stage.getContext("2d");</script>',
            "builds its drawing in the script (getContext)",
        ),
        (
            '<script>const cloth = document.createElementNS("http://www.w3.org/2000/svg", "rect");</script>',
            "builds its drawing in the script (createElementNS)",
        ),
        ("<script>cloth.setAttribute('fill', 'saddlebrown');</script>", "names the colour 'saddlebrown'"),
        ('<script>cloth.style.backgroundColor = "peru";</script>', "names the colour 'peru'"),
        (
            '<script>cloth.style.setProperty("fill", "var(--dye-indigo)");</script>',
            "paints --dye-indigo by hand",
        ),
        ('<script>cloth.setAttribute("style", "stroke: tan");</script>', "names the colour 'tan'"),
        ('<svg viewBox="0 0 10 10"><rect fill="peru"></rect></svg>', "names the colour 'peru'"),
        ('<svg viewBox="0 0 10 10"><g opacity="0.4"></g></svg>', "rests at opacity 0.4"),
        ('<svg viewBox="0 0 10 10"><rect fill-opacity=".5"></rect></svg>', "rests at fill-opacity .5"),
        ("<style>.unplayed{stroke-opacity:40%}</style>", "rests at stroke-opacity 40%"),
    ],
)
def test_a_figure_drawn_outside_the_static_svg_or_faded_at_rest_is_refused(html: str, said: str) -> None:
    assert any(said in detail for detail in details(html))


@pytest.mark.parametrize(
    "html",
    [
        '<script>said.textContent = "Deep fast chocolate-black colour"; label.textContent = "Indigo";</script>',
        '<script>bar.setAttribute("fill", "var(--chart-emph)"); chip.style.color = "var(--ink-2)";</script>',
        '<script>const chip = document.createElement("span");</script>',
        AT.replace('<rect x="0"', '<rect opacity="1" fill-opacity="100%" x="0"'),
    ],
)
def test_words_that_name_a_colour_a_script_painting_a_role_and_a_still_figure_pass(html: str) -> None:
    assert details(html) == []


@pytest.mark.parametrize(
    "html",
    [
        "<style>.a{accent-color:var(--indigo);border:1px solid var(--rule-strong)}</style>",
        "<style>.a{font:inherit;opacity:1;color:currentColor}</style>",
        '<script>if (document.documentElement.dataset.reducedMotion !== "true") setTimeout(go, 1000);</script>',
        '<div role="img" aria-label="Fall at the lower stated rate"></div>',
        "<p>Up to <strong>15</strong> feet.</p>",
    ],
)
def test_a_control_in_indigo_a_still_timer_and_plain_words_pass(html: str) -> None:
    assert details(html) == []


@pytest.mark.parametrize(
    ("html", "said"),
    [
        (
            "<style>:root{--ink-1:var(--dye-indigo)}</style>",
            "declares --ink-1, a token the frame takes from the page",
        ),
        (
            "<style>:root{--c-ink-1:30 60 200}</style>",
            "declares --c-ink-1, a token the frame takes from the page",
        ),
        (
            '<script>document.documentElement.style.setProperty("--sunk", "var(--chart-emph)");</script>',
            "declares --sunk, a token the frame takes from the page",
        ),
        (
            '<svg viewBox="0 0 10 10"><g style="--rule: var(--chart-series)"></g></svg>',
            "declares --rule, a token the frame takes from the page",
        ),
        ("<style>.a{--cloth:var(--dye-indigo)}</style>", "paints --dye-indigo by hand"),
        ("<style>.a{--edge:#2f5d8a}</style>", "names the colour '#2f5d8a'"),
    ],
)
def test_a_token_the_frame_takes_from_the_page_is_never_redeclared_and_an_own_property_holds_no_colour(
    html: str, said: str
) -> None:
    assert any(said in detail for detail in details(html))


@pytest.mark.parametrize(
    "html",
    [
        "<style>.kv{--gap:8px;--k:1;gap:var(--gap)}</style>",
        "<style>.kv{--line:var(--ink-2)}</style>",
    ],
)
def test_a_custom_property_for_layout_or_naming_a_design_role_passes(html: str) -> None:
    assert details(html) == []


DATA_IMAGE = "shows a data: image, which the bar cannot read as a drawing"


@pytest.mark.parametrize(
    "html",
    [
        '<img src="data:image/png;base64,iVBORw0KGgo=" alt="Water level">',
        '<img src="data&#58;image/svg+xml,%3Csvg%3E%3C/svg%3E" alt="Cloth">',
        '<style>.a{background:url("data:image/svg+xml,%3Csvg%3E%3C/svg%3E")}</style>',
        '<svg viewBox="0 0 10 10"><image href="data:image/gif;base64,R0lGODlh" width="10" height="10"></image></svg>',
        '<script>picture.setAttribute("src", "data:image/webp;base64,UklGR");</script>',
    ],
)
def test_a_data_image_is_refused_since_the_bar_cannot_read_it_and_no_switch_holds_it_still(html: str) -> None:
    assert any(detail.startswith(DATA_IMAGE) for detail in details(html))


def test_words_about_data_and_an_image_are_not_a_data_image() -> None:
    assert details("<p>The data from the well and an image of it.</p>") == []
