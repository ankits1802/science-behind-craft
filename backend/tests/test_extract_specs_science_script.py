import pytest

from app.core.errors import InvalidInput
from app.scripts.extract_specs_science_dom import find_anchor, parse_fragment
from app.scripts.extract_specs_science_read import drawing, rich, unit_of
from app.scripts.extract_specs_science_stages import stage_tile

FIGURE = (
    '<figure id="f"><svg viewBox="0 0 2 2" data-fit><linearGradient id="g"/><text>2 H</text>\n'
    '<text> + 2 e<tspan>−</tspan></text></svg><input type="range" value="7"><p data-x="a &amp; b">'
    '<kv-slot unit="u0042"></kv-slot></p><style>.a > b { font: "Plex" }</style></figure>'
)


def test_the_template_parser_keeps_drawing_names_as_written() -> None:
    svg = find_anchor(parse_fragment(FIGURE), "#f").elements[0]
    assert svg.attrs == {"viewBox": "0 0 2 2", "data-fit": ""}
    assert svg.elements[0].tag == "linearGradient"


def test_void_elements_close_themselves_and_style_text_is_kept_raw() -> None:
    figure = find_anchor(parse_fragment(FIGURE), "#f")
    assert [element.tag for element in figure.elements] == ["svg", "input", "p", "style"]
    assert figure.elements[3].text() == '.a > b { font: "Plex" }'


def test_attributes_are_read_unescaped_and_a_unit_slot_names_its_unit() -> None:
    paragraph = find_anchor(parse_fragment(FIGURE), '[data-x="a & b"]')
    assert unit_of(paragraph) == "u0042"


def test_an_anchor_matches_exactly_one_element() -> None:
    root = parse_fragment('<p class="a"></p><p class="a"></p>')
    with pytest.raises(InvalidInput, match="matches 2 elements"):
        find_anchor(root, '[class="a"]')
    with pytest.raises(InvalidInput, match="matches 0 elements"):
        find_anchor(root, "#missing")


def test_a_template_that_does_not_close_its_elements_is_refused() -> None:
    with pytest.raises(InvalidInput):
        parse_fragment("<div><p></div>")


def test_a_drawing_drops_layout_newlines_but_keeps_the_spaces_inside_its_text() -> None:
    svg = find_anchor(parse_fragment(FIGURE), "#f").elements[0]
    assert drawing(svg)["children"] == [
        {"tag": "linearGradient", "attrs": {"id": "g"}},
        {"tag": "text", "children": ["2 H"]},
        {"tag": "text", "children": [" + 2 e", {"tag": "tspan", "children": ["−"]}]},
    ]


def test_rich_text_is_runs_of_plain_and_styled_text() -> None:
    formula = parse_fragment("<b>KAl(SO<sub>4</sub>)<sub>2</sub>·12H<sub>2</sub>O</b>").elements[0]
    assert rich(formula.children) == [
        "KAl(SO",
        {"text": "4", "style": "sub"},
        ")",
        {"text": "2", "style": "sub"},
        "·12H",
        {"text": "2", "style": "sub"},
        "O",
    ]
    with pytest.raises(InvalidInput):
        rich(parse_fragment('<b><span class="x">C</span></b>').elements[0].children)


def test_a_stage_tile_is_the_cloth_pattern_of_its_stage_over_the_weave() -> None:
    assert stage_tile("rb-svg", "0 0 100 150", 3) == {
        "tag": "svg",
        "attrs": {
            "class": "rb-svg",
            "viewBox": "0 0 100 150",
            "preserveAspectRatio": "xMidYMid slice",
            "aria-hidden": "true",
        },
        "children": [
            {
                "tag": "rect",
                "attrs": {"x": "-200", "y": "-200", "width": "800", "height": "800", "fill": "url(#tile-3)"},
            },
            {
                "tag": "rect",
                "attrs": {
                    "x": "-200",
                    "y": "-200",
                    "width": "800",
                    "height": "800",
                    "fill": "url(#pt-weave)",
                },
            },
        ],
    }
