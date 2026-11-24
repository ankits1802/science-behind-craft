import pytest

from app.research.colour_key import DEPICTED_COLOURS, depicted_material
from app.research.colours import COLOUR_WORDS
from app.research.depicted_materials import DEPICTED_MATERIALS


def test_each_key_token_is_a_depicted_material_of_one_colour_word() -> None:
    assert set(DEPICTED_COLOURS) <= set(DEPICTED_MATERIALS)
    assert {depicted.colour for depicted in DEPICTED_COLOURS.values()} <= set(COLOUR_WORDS)
    assert all(depicted.substances for depicted in DEPICTED_COLOURS.values())


@pytest.mark.parametrize(
    ("colour", "names", "token"),
    [
        ("BLUE", ["Indigo"], "indigo"),
        ("GREEN", ["Indigo"], "leuco"),
        ("RED", ["Al root", "Alizarin", "Madder"], "madder"),
        ("RED", ["Indian madder", "Rubia cordifolia"], "madder"),
        ("BLACK", ["Ferrous sulphate", "Scrap iron"], "kut"),
        ("YELLOW", ["Myrobalan (harda)"], "harda"),
        ("WHITE", ["Gum arabic (babul gum)", "Lime"], "lime"),
        ("BLUE", ["Cobalt oxide"], "cobalt"),
    ],
)
def test_a_colour_draws_the_token_that_depicts_its_named_substance(
    colour: str, names: list[str], token: str
) -> None:
    assert depicted_material(colour, names) == token


@pytest.mark.parametrize(
    ("colour", "names"),
    [
        ("YELLOW", ["Turmeric", "Curcuma longa"]),
        ("BLACK", ["Iron", "Madder"]),
        ("BLACK", ["Ferrous", "sulphate"]),
        ("RED", ["Indigo"]),
        ("WHITE", ["Camel dung", "Castor oil"]),
        ("BLUE", []),
        (None, ["Indigo"]),
    ],
)
def test_a_colour_no_token_depicts_draws_none(colour: str | None, names: list[str]) -> None:
    assert depicted_material(colour, names) is None
