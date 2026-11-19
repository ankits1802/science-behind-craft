from typing import Any

import pytest
from pydantic import ValidationError

from app.research.component_specs_data import SPEC_MODELS_DATA

SVG = {
    "tag": "svg",
    "attrs": {"viewBox": "0 0 560 168"},
    "children": [{"tag": "line", "attrs": {"x1": "0", "x2": "10"}}],
}
HEAD = {"number": {"unit": "u0839", "ref": "pt:7"}, "title": "u0840", "titleId": "yd-t"}
LINE = {"tag": "p", "classes": ["rs-t"], "unit": "u0597"}
HELD_LINE = {"tag": "p", "classes": ["ws-t"], "text": ["Ajrakhpur was founded in 2001."]}
TOGGLES = {
    "classes": ["seg"],
    "label": "Map layer",
    "marker": "layers",
    "optionKey": "layer",
    "options": [
        {"value": "rain", "label": "Rainfall", "pressed": True},
        {"value": "temp", "label": "Temperature", "pressed": False},
    ],
}
EXPLORER = {
    "head": {
        "number": {"unit": "u0590", "ref": "pt:3"},
        "title": "u0591",
        "titleId": "fig3-t",
        "dek": "u0592",
    },
    "id": "b-rs",
    "comp": "region",
    "controls": [TOGGLES],
    "mapLabel": "Kachchh and the districts around it",
    "drawing": SVG,
    "inset": {"drawing": SVG, "caption": "u0593"},
    "key": {"id": "b-map-k", "unit": "u0594"},
    "caption": "u0595",
    "side": [LINE, HELD_LINE],
    "rank": {"caption": "u0601", "more": "Show all 27"},
}
CARD = {
    "visual": "kutch-ajrakh/geography/suran-flowing-north-map",
    "when": "u0605",
    "title": "u0606",
    "lines": [LINE],
}
EVENT = {
    "view": "corridor",
    "routes": [],
    "pins": ["Dhamadka"],
    "when": "1586 to 1631",
    "title": "A king's invitation",
}
EVENT_CARD = {
    "when": "u0750",
    "title": "u0751",
    "lines": [{"tag": "p", "classes": ["tl-t"], "unit": "u0752"}],
}
TIMELINE_MAP = {
    "head": {
        "number": {"unit": "u0737", "ref": "pt:1"},
        "title": "u0738",
        "titleId": "fig1-t",
        "dek": "u0739",
    },
    "id": "c-tl",
    "comp": "time",
    "rest": 0,
    "events": [EVENT],
    "play": "Play the timeline",
    "status": "u0740",
    "supply": {"labelId": "c-sup-l", "label": "Material sources", "description": "Indigo from Shikarpur"},
    "views": {"world": [0, 0, 1000, 546.71]},
    "drawing": SVG,
    "legend": [{"swatch": ["lg-k"], "label": "Kachchh"}],
    "caption": "u0741",
    "cards": [EVENT_CARD],
    "supplyNote": [{"tag": "p", "classes": ["tl-t"], "unit": "u0783"}],
    "axis": {
        "label": "Dated moments",
        "ticks": [{"left": "10.00%", "text": "1000"}],
        "events": [{"row": 0, "left": "33.53%", "short": "1586–1631"}],
    },
    "items": [EVENT_CARD],
}
LISTED = {
    "key": "g45",
    "number": 45,
    "title": "Form GI-1: Bagru Hand Block Print",
    "meta": "GI Registry, 2009",
    "grade": "A",
    "gradeLabel": "A · peer-reviewed or official",
    "sentences": 1,
    "url": "https://origin-gi.com/a.pdf",
    "linkLabel": ": Form GI-1",
}
PANEL = {
    "key": "answer",
    "tabId": "kv-ct-a",
    "panelId": "kv-cp-a",
    "label": "This answer",
    "box": ["bx", "bx-rm"],
    "aid": "end",
    "cites": ["kv-cites"],
    "styleKey": "style",
    "styles": [{"value": "apa", "label": "APA", "text": "KalaVigyan. (2026)."}],
    "textId": "cb-text",
    "text": "u0990",
    "link": "u0991",
    "copyLabel": "Copy citation",
}
READINGS = [{"who": "Clifford, 2012", "unit": "u0568"}, {"who": "Karolia and Buch, 2008", "unit": "u0567"}]

VALID: dict[str, dict[str, Any]] = {
    "chart": {
        "form": "rows",
        "rows": {
            "classes": ["yard"],
            "head": HEAD,
            "rows": [{"label": "Fabindia", "value": 70000, "shown": "70,000 m", "emphasis": True}],
            "source": "u0841",
        },
    },
    "stat_tiles": {
        "classes": ["three"],
        "tiles": [{"figure": "Rs 1.5", "small": "crore", "caption": "u0629"}],
    },
    "fact_table": {
        "id": "glance",
        "numeral": 1,
        "chapterNo": "u0055",
        "title": "u0056",
        "titleId": "glance-h",
        "rows": [{"term": "u0057", "value": "u0058"}],
    },
    "map_layer": {"setting": "explorer", "explorer": EXPLORER},
    "map_sequence": {
        "head": HEAD,
        "first": [{"card": CARD}, {"component": "kutch-ajrakh/chemistry/iron-on-purpose-and-by-accident"}],
        "source": {"classes": ["src-line"], "unit": "u0618"},
    },
    "timeline": {
        "variant": "gi",
        "number": {"unit": "u0847", "ref": "pt:6"},
        "title": "u0848",
        "scale": {
            "label": "Application to certificate",
            "marks": [{"left": "0%"}, {"left": "100%", "final": True}],
        },
        "steps": ["u0849"],
    },
    "timeline_map": TIMELINE_MAP,
    "concept_atlas": {
        "title": "u0925",
        "description": "u0926",
        "groups": [
            {
                "id": "ss-alum",
                "title": "u0944",
                "text": "u0945",
                "together": "u0946",
                "first": [
                    {
                        "name": "Bagh Prints",
                        "place": "Madhya Pradesh",
                        "family": "Textiles",
                        "sentences": 10,
                        "sentence": {"classes": ["res-s"], "unit": "u0947"},
                    }
                ],
            }
        ],
    },
    "related_crafts": {
        "title": "u0919",
        "kicker": "Shared materials and methods",
        "description": "u0920",
        "weave": "pt-weave",
        "crafts": [
            {
                "tile": 6,
                "swatch": ["Ajrakh after pa"],
                "top": "Hand Block Printing",
                "name": "Bagru",
                "place": "Rajasthan",
                "sources": 12,
                "monograph": True,
                "gi": True,
                "shares": ["Shares Alum"],
                "sentence": "u0921",
            }
        ],
    },
    "source_list": {
        "setting": "listing",
        "listing": {
            "id": "kv-src-kin",
            "title": "u1066",
            "description": "u1067",
            "openLabel": "Show the sources",
            "closeLabel": "Hide them",
            "sources": [LISTED],
        },
    },
    "source_disagreements": {
        "id": "differ",
        "titleId": "dif-h",
        "title": "Experts differ",
        "intro": "u0564",
        "items": [{"summary": ["Sources differ: how long the vat ferments"], "readings": READINGS}],
    },
    "citation_tool": {
        "title": "u0989",
        "titleId": "kv-cite-h",
        "tabsLabel": "What to cite",
        "panels": [PANEL],
    },
}

REFUSED: dict[str, tuple[dict[str, Any], str]] = {
    "chart": (
        {"form": "dots", "dots": {"classes": ["dots45"], "label": "Khatris", "total": 4, "marked": 5}},
        "no more dots",
    ),
    "stat_tiles": ({"tiles": []}, "at least 1"),
    "fact_table": ({**VALID["fact_table"], "numeral": 0}, "greater than or equal to 1"),
    "map_layer": ({"setting": "drawing", "explorer": EXPLORER}, "drawn map layer"),
    "map_sequence": (
        {
            **VALID["map_sequence"],
            "first": [{"card": CARD, "component": "kutch-ajrakh/chemistry/iron-on-purpose-and-by-accident"}],
        },
        "not both or neither",
    ),
    "timeline": (
        {**VALID["timeline"], "scale": {"label": "x", "marks": [{"left": "left"}, {"left": "1%"}]}},
        "pattern",
    ),
    "timeline_map": (
        {**TIMELINE_MAP, "items": [EVENT_CARD, EVENT_CARD]},
        "one card, list item and axis mark",
    ),
    "concept_atlas": ({**VALID["concept_atlas"], "groups": []}, "at least 1"),
    "related_crafts": ({**VALID["related_crafts"], "weave": "pt weave"}, "pattern"),
    "source_list": (
        {
            "setting": "listing",
            "listing": {
                **VALID["source_list"]["listing"],
                "sources": [{**LISTED, "url": "http://example.org"}],
            },
        },
        "https",
    ),
    "source_disagreements": (
        {**VALID["source_disagreements"], "items": [{"summary": ["x"], "readings": READINGS[:1]}]},
        "at least 2",
    ),
    "citation_tool": ({**VALID["citation_tool"], "panels": [PANEL, PANEL]}, "its own id"),
}


def test_the_data_group_names_a_model_for_each_of_its_twelve_kinds() -> None:
    assert sorted(SPEC_MODELS_DATA) == sorted(
        [
            "chart",
            "stat_tiles",
            "fact_table",
            "map_layer",
            "map_sequence",
            "timeline",
            "timeline_map",
            "concept_atlas",
            "related_crafts",
            "source_list",
            "source_disagreements",
            "citation_tool",
        ]
    )


@pytest.mark.parametrize("kind", sorted(VALID))
def test_a_valid_spec_of_each_kind_is_accepted(kind: str) -> None:
    SPEC_MODELS_DATA[kind].model_validate(VALID[kind])


@pytest.mark.parametrize("kind", sorted(REFUSED))
def test_a_spec_breaking_its_kinds_rule_is_refused(kind: str) -> None:
    spec, reason = REFUSED[kind]
    with pytest.raises(ValidationError, match=reason):
        SPEC_MODELS_DATA[kind].model_validate(spec)


def test_a_toggle_group_presses_exactly_one_option() -> None:
    both = {**TOGGLES, "options": [{**option, "pressed": True} for option in TOGGLES["options"]]}
    with pytest.raises(ValidationError, match="exactly one option pressed"):
        SPEC_MODELS_DATA["map_layer"].model_validate(
            {"setting": "explorer", "explorer": {**EXPLORER, "controls": [both]}}
        )


def test_a_series_keeps_whole_numbers_whole() -> None:
    spec = SPEC_MODELS_DATA["timeline_map"].model_validate(TIMELINE_MAP)
    assert spec.model_dump(mode="json", by_alias=True)["views"] == {"world": [0, 0, 1000, 546.71]}
