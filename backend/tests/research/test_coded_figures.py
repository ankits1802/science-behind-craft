import json
import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from app.data.kind_fixture_files import KIND_FIXTURES_DIR
from app.research.coded_figure_code import CODE_MAX_BYTES
from app.research.coded_figure_still import code_still, still_node, worded_still
from app.research.component_specs import CONTRIBUTABLE_KINDS, checked_spec
from app.research.component_specs_general_delivery import DeliveredUnit, spec_problems
from app.research.component_specs_science_coded import CodedFigureSpec
from app.research.page_render import INTERACTIVE_KINDS
from app.services.drawing_themes import themed_spec

KIND = "coded_figure"
FIXTURE = json.loads((KIND_FIXTURES_DIR / "coded_figure.json").read_text(encoding="utf-8"))
SCRIPT_START = "(function () {\n"
FLAG_READ = 'document.documentElement.dataset.reducedMotion === "true"'
CANVAS = (
    "<canvas></canvas><script>\n(function () {\nconst data = JSON.parse(document.getElementById"
    '("kv-data").textContent);\nconst still = document.documentElement.dataset.reducedMotion;\n'
    "})();\n</script>"
)
STILL = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60"><rect x="4" y="4" width="40" height="20" '
    'fill="#3a5f8f" /><text x="8" y="50" data-unit="patina" /></svg>'
)


def _units() -> dict[str, DeliveredUnit]:
    ids = {key: uuid.uuid5(uuid.NAMESPACE_URL, f"Bidriware/{key}") for key in FIXTURE["facts"]}
    return {
        ref: DeliveredUnit(text=unit["text"], claim_ids=[ids[claim] for claim in unit["claims"]])
        for ref, unit in FIXTURE["units"].items()
    }


def _spec(**changes: Any) -> dict[str, Any]:
    return {**FIXTURE["spec"], **changes}


def _code(old: str, new: str) -> dict[str, Any]:
    code = FIXTURE["spec"]["code"]
    assert old in code
    return _spec(code=code.replace(old, new, 1))


def _in_script(line: str) -> dict[str, Any]:
    return _code(SCRIPT_START, SCRIPT_START + line + "\n")


def test_the_coded_figure_is_a_contributable_interactive_kind() -> None:
    assert KIND in CONTRIBUTABLE_KINDS
    assert KIND in INTERACTIVE_KINDS


def test_a_figure_drawing_only_from_its_data_is_accepted_with_free_labels() -> None:
    assert spec_problems(KIND, FIXTURE["spec"], _units()) == []
    figure = checked_spec(KIND, FIXTURE["spec"])
    assert isinstance(figure, CodedFigureSpec)
    assert [value.key for value in figure.values] == ["ammonium", "nitrate", "water"]
    assert ">Play</button>" in figure.code and ">Bidri alloy</text>" in figure.code


@pytest.mark.parametrize(
    ("spec", "reason"),
    [
        (_in_script('fetch("/api/crafts");'), "the code uses fetch, which the frame refuses"),
        (_in_script("const crumbs = document.cookie;"), "the code uses cookie, which the frame refuses"),
        (_in_script('top.location.href = "#";'), "the code uses location, which the frame refuses"),
        (_in_script("localStorage.clear();"), "the code uses localStorage, which the frame refuses"),
        (
            _code("</script>", '</script><script src="https://cdn.example/x.js"></script>'),
            "a script element with attributes",
        ),
        (_code("<ul ", "<p>Leave it for 48 hours</p><ul "), "the code shows 48"),
        (_in_script('status.textContent = "Leave the piece for 48 hours";'), "the code shows 48"),
        (
            _code(
                "<ul ",
                "<p>The black patina on the alloy comes from the soil of the old fort at Bidar, which no "
                "other soil gives</p><ul ",
            ),
            "in words of its own",
        ),
        (_code(FLAG_READ, "false"), "without reading document.documentElement.dataset.reducedMotion"),
        (_spec(code=CANVAS), "the code draws no svg to cut its still from"),
        (
            _code("<ul ", '<span data-unit="boil"></span><ul '),
            "'boil' by data-unit, which texts does not hold",
        ),
        (_spec(map={"layers": ["rivers"]}), "declares a map but holds no svg with data-map"),
        (_code("<ul ", '<video data-film="dip"></video><ul '), "<video>, which the frame refuses"),
        (_code("<ul ", '<p id="kv-words"></p><ul '), "id kv-words, which the frame keeps"),
    ],
)
def test_a_figure_that_reaches_out_or_states_a_fact_of_its_own_is_refused_with_its_reason(
    spec: dict[str, Any], reason: str
) -> None:
    problems = spec_problems(KIND, spec, _units())
    assert problems and reason in problems[0], problems


def test_the_code_is_held_to_its_budget() -> None:
    padded = FIXTURE["spec"]["code"] + " " * CODE_MAX_BYTES
    with pytest.raises(ValidationError, match=r"at most \d+ characters"):
        checked_spec(KIND, _spec(code=padded))


def test_a_value_is_stated_by_its_reading_and_a_library_is_one_the_site_pins() -> None:
    values = [{**FIXTURE["spec"]["values"][0], "value": 21.0}, *FIXTURE["spec"]["values"][1:]]
    assert "the value 21 is not stated by its unit u0004" in spec_problems(
        KIND, _spec(values=values), _units()
    )
    assert spec_problems(KIND, _spec(libraries=["d3", "three"]), _units()) == []
    assert "libraries.0" in spec_problems(KIND, _spec(libraries=["jquery"]), _units())[0]


def test_a_canvas_figure_sends_its_still_and_a_film_is_one_the_site_serves() -> None:
    accepted = checked_spec(KIND, _spec(code=CANVAS, values=[], still=STILL))
    assert isinstance(accepted, CodedFigureSpec) and accepted.still is not None
    filmed = _code("<ul ", '<video data-film="dip" controls></video><ul ')
    films = [{"key": "dip", "src": "/monographs/kit/films/bidri-dip.mp4"}]
    assert spec_problems(KIND, {**filmed, "films": films}, _units()) == []
    elsewhere = [{"key": "dip", "src": "https://cdn.example/dip.mp4"}]
    assert "films.0.src" in spec_problems(KIND, {**filmed, "films": elsewhere}, _units())[0]


def test_a_map_figure_takes_the_site_base_and_a_hand_drawn_map_is_refused() -> None:
    mapped = _code('<svg viewBox="0 0 320 200"', '<svg viewBox="0 0 320 200" data-map=""')
    assert (
        spec_problems(KIND, {**mapped, "map": {"layers": ["states", "rivers"], "districts": [468]}}, _units())
        == []
    )
    dots = "".join(f'<circle cx="{x}" cy="60" r="4" fill="var(--terracotta)"/>' for x in (20, 40, 60))
    drawn = _code("</svg>", dots + "</svg>")
    assert any("draws a map by hand" in problem for problem in spec_problems(KIND, drawn, _units()))


def test_the_server_cuts_the_still_from_the_code_and_serves_it_in_four_themes() -> None:
    still = code_still(FIXTURE["spec"]["code"])
    assert still is not None and still.startswith(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200"'
    )
    served = themed_spec(KIND, FIXTURE["spec"])
    assert served["still"] == still
    assert list(served["themes"]) == ["light", "dark", "hcLight", "hcDark"]
    assert "var(--ink-1)" not in served["themes"]["light"]
    assert checked_spec(KIND, served).still == still
    given = themed_spec(KIND, _spec(code=CANVAS, still=STILL))
    assert given["still"] == checked_spec(KIND, _spec(code=CANVAS, still=STILL)).still


def test_a_still_shows_its_words_where_its_text_names_a_unit() -> None:
    node = still_node(checked_spec(KIND, _spec(code=CANVAS, still=STILL)).still or "")
    worded = worded_still(node, {"patina": "The black patina forms instantly on immersion"})
    (text,) = [child for child in worded["children"] if child["tag"] == "text"]
    assert text["children"] == ["The black patina forms instantly on immersion"]


def test_a_number_in_a_sent_still_is_one_of_its_values() -> None:
    numbered = STILL.replace('<text x="8" y="50" data-unit="patina" />', '<text x="8" y="50">48 hours</text>')
    assert (
        "the code shows 48" in spec_problems(KIND, _spec(code=CANVAS, values=[], still=numbered), _units())[0]
    )
