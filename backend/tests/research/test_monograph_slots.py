import pytest

from app.core.errors import InvalidInput
from app.research.monograph_page import (
    MonographContent,
    PageParts,
    TextUnit,
    assemble_template,
    keyed_kit,
    kit_parts,
    kit_source,
    render_fragment,
    render_page,
    served_kit,
)

OUTER = "t/x/outer"
INNER = "t/x/inner"
SHELL = (
    '<style><kv-slot kit="monograph.css#page"></kv-slot></style>'
    '<main><kv-slot component="t/x/outer"></kv-slot></main>'
)
FRAGMENTS = {
    OUTER: '<figure id="o"><kv-slot unit="u1"></kv-slot><kv-slot component="t/x/inner"></kv-slot></figure>',
    INNER: '<div id="i"><kv-slot unit="u2"></kv-slot><script><kv-slot data="film"></kv-slot></script></div>',
}
PARTS = PageParts(fragments=FRAGMENTS, kit={"monograph.css#page": "p{color:red}"})
CSS = "@kv-part page;\n:root{}\nb{}\n\n@kv-part release-fixes;\nsvg{}\n"
JS = '"kv-part page";\n(function(){})();\n\n"kv-part boxes";\nKV.boot();\n'


def _unit(text: str) -> TextUnit:
    return TextUnit(chapter="answer", tag="p", field="OVERVIEW", nodes=[text], claim_ids=[])


CONTENT = MonographContent(
    craft_slug="Kutch-Ajrakh",
    sources={},
    citations={},
    citation_claims={},
    data={"film": {"a": 1}},
    units={"u1": _unit("Ajrakh & indigo"), "u2": _unit("Alum")},
    components=[],
    layout=[],
)


def test_a_page_draws_each_component_from_its_fragment_and_inlines_the_kit() -> None:
    assert render_page(SHELL, CONTENT, parts=PARTS) == (
        "<style>p{color:red}</style><main>"
        '<figure id="o">Ajrakh &amp; indigo<div id="i">Alum<script>{"a": 1}</script></div></figure></main>'
    )


def test_a_fragment_fills_its_units_and_keeps_the_slot_of_a_component_inside_it() -> None:
    assert render_fragment(FRAGMENTS[OUTER], CONTENT) == (
        '<figure id="o">Ajrakh &amp; indigo<kv-slot component="t/x/inner"></kv-slot></figure>'
    )


def test_the_shell_and_parts_assemble_into_the_template_with_its_unit_and_data_slots() -> None:
    assert assemble_template(SHELL, PARTS) == (
        '<style>p{color:red}</style><main><figure id="o"><kv-slot unit="u1"></kv-slot>'
        '<div id="i"><kv-slot unit="u2"></kv-slot><script><kv-slot data="film"></kv-slot></script></div>'
        "</figure></main>"
    )


@pytest.mark.parametrize(
    ("template", "parts"),
    [
        ('<kv-slot component="t/x/gone"></kv-slot>', PARTS),
        (
            '<kv-slot component="t/x/self"></kv-slot>',
            PageParts(fragments={"t/x/self": '<i><kv-slot component="t/x/self"></kv-slot></i>'}),
        ),
        ('<style><kv-slot kit="monograph.css#gone"></kv-slot></style>', PARTS),
    ],
    ids=["a component without a fragment", "a fragment holding its own slot", "a kit part the kit lacks"],
)
def test_a_slot_with_nothing_to_fill_it_is_refused(template: str, parts: PageParts) -> None:
    with pytest.raises(InvalidInput):
        render_page(template, CONTENT, parts=parts)


def test_a_fragment_may_not_hold_the_page_wide_kit() -> None:
    with pytest.raises(InvalidInput, match="page-wide"):
        render_fragment('<div><kv-slot kit="monograph.css#page"></kv-slot></div>', CONTENT)


def test_a_kit_file_is_its_parts_each_after_its_marker_line_and_before_a_newline() -> None:
    assert kit_parts(CSS, file_name="monograph.css") == {"page": ":root{}\nb{}\n", "release-fixes": "svg{}"}
    assert kit_parts(JS, file_name="monograph.js") == {"page": "(function(){})();\n", "boxes": "KV.boot();"}
    assert kit_source({"page": ":root{}\nb{}\n", "release-fixes": "svg{}"}, file_name="monograph.css") == CSS
    assert served_kit(CSS, file_name="monograph.css") == ":root{}\nb{}\nsvg{}"
    assert keyed_kit({"monograph.js": JS}) == {
        "monograph.js#page": "(function(){})();\n",
        "monograph.js#boxes": "KV.boot();",
    }


@pytest.mark.parametrize(
    ("source", "file_name"),
    [
        (":root{}\n@kv-part page;\nb{}\n", "monograph.css"),
        ("@kv-part page;\nb{}\n@kv-part page;\ni{}\n", "monograph.css"),
        ("@kv-part page;\nb{}", "monograph.css"),
        ("@kv-part page;\nb{}\n", "monograph.txt"),
    ],
    ids=[
        "text before the first marker",
        "a part named twice",
        "a part without its newline",
        "no marker for the file",
    ],
)
def test_a_malformed_kit_file_is_refused(source: str, file_name: str) -> None:
    with pytest.raises(InvalidInput):
        kit_parts(source, file_name=file_name)


def test_a_kit_part_holding_a_marker_line_is_refused() -> None:
    with pytest.raises(InvalidInput, match="hold a part marker"):
        kit_source({"page": "b{}\n@kv-part sneaked;\n"}, file_name="monograph.css")
