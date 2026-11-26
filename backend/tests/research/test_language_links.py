from typing import Any

import pytest
from pydantic import ValidationError

from app.research.component_specs import CONTRIBUTABLE_KINDS, not_contributable
from app.research.component_specs_tools import LanguageSwitchSpec
from app.scripts.extract_specs_tools import tool_specs

AJRAKH_LANGUAGES = "kutch-ajrakh/overview/answer-in-hindi-and-urdu"


def option(lang: str, href: str | None) -> dict[str, Any]:
    linked = {"href": href} if href is not None else {}
    return {"lang": lang, "name": lang, "direction": "ltr", "status": lang, **linked}


def linked(**changes: Any) -> dict[str, Any]:
    return {
        "label": "Read this page in",
        "options": [option("en", "/crafts/Bagh-Print"), option("hi", "/crafts/Bagh-Print/hi")],
        **changes,
    }


def test_a_switch_of_the_page_s_languages_links_each_option_and_holds_no_panel() -> None:
    spec = LanguageSwitchSpec.model_validate(linked())
    assert [option.href for option in spec.options] == ["/crafts/Bagh-Print", "/crafts/Bagh-Print/hi"]
    assert spec.english is None and spec.panels == []
    assert LanguageSwitchSpec.model_validate(
        linked(options=[option("en", "/categories/Textiles"), option("hi", "/categories/Textiles/hi")])
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"options": [option("en", "/crafts/Bagh-Print"), option("hi", None)]},
        {"english": "u0001"},
        {
            "options": [
                option("en", "https://elsewhere.example/crafts/Bagh-Print"),
                option("hi", "/crafts/Bagh-Print/hi"),
            ]
        },
        {"options": [option("en", "/crafts/Bagh-Print/monograph/hi"), option("hi", "/crafts/Bagh-Print/hi")]},
    ],
)
def test_a_half_linked_switch_one_with_an_english_unit_or_one_leaving_the_site_is_refused(
    changes: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        LanguageSwitchSpec.model_validate(linked(**changes))


def test_kutch_ajrakh_s_switch_of_panels_still_holds_and_needs_its_english_unit() -> None:
    spec = tool_specs("Kutch-Ajrakh")[AJRAKH_LANGUAGES]
    shown = LanguageSwitchSpec.model_validate(spec)
    assert shown.english is not None and len(shown.panels) == len(shown.options) - 1
    unlinked = {key: value for key, value in spec.items() if key != "english"}
    with pytest.raises(ValidationError, match="links every option"):
        LanguageSwitchSpec.model_validate(unlinked)


def test_the_student_version_is_delivered_and_the_site_s_reading_tools_are_not() -> None:
    assert "reading_level" in CONTRIBUTABLE_KINDS and not_contributable("reading_level") is None
    assert "quiz" not in CONTRIBUTABLE_KINDS and not_contributable("quiz") is not None
    for kind in ("ask_next", "language_switch"):
        assert kind not in CONTRIBUTABLE_KINDS
        assert not_contributable(kind) == (
            f"the site builds the {kind} of every page from its data, so it is never delivered"
        )
