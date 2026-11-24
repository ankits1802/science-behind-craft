import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.data.specimen_records import specimen_records
from app.research.colour_key import (
    DEPICTED_COLOURS,
    agent_materials,
    agent_names,
    depicted_material,
    first_depicted,
    specimen_token,
)
from app.research.colours import COLOUR_WORDS, states_colour
from app.research.depicted_materials import DEPICTED_MATERIALS

DOSSIERS = Path(__file__).resolve().parents[2] / "app" / "data" / "curation"
RECORDED_FROM_THEIR_FACTS = (
    "turmeric",
    "pomegranate",
    "kali-mitti",
    "cinnabar",
    "red-ochre",
    "orpiment",
    "lamp-black",
    "conch-white",
)


@dataclass(frozen=True)
class Material:
    name: str
    role: str | None
    botanical_name: str | None = None
    local_names: tuple[str, ...] = ()


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
        ("BLACK", ["Syahi, the iron-black mordant paste", "syahee"], "kut"),
        ("BLACK", ["Kasim (fermented iron and jaggery black)", "kasam"], "kut"),
        ("YELLOW", ["Myrobalan (harda)"], "harda"),
        ("YELLOW", ["Turmeric", "Curcuma longa"], "turmeric"),
        ("YELLOW", ["Pomegranate rind", "naspal"], "pomegranate"),
        ("YELLOW", ["Orpiment", "haritala"], "orpiment"),
        ("BLACK", ["Black clay", "kali mitti"], "kali-mitti"),
        ("BLACK", ["Lamp black", "kala"], "lamp-black"),
        ("RED", ["Cinnabar", "hingula"], "cinnabar"),
        ("RED", ["Red ochre", "geru"], "red-ochre"),
        ("WHITE", ["Gum arabic (babul gum)", "Lime"], "lime"),
        ("WHITE", ["Conch shell", "sankh"], "conch-white"),
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
        ("YELLOW", ["Marigold flowers"]),
        ("RED", ["Aal root", "aal"]),
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


def test_a_stage_s_agents_are_its_dyes_mordants_and_resists_named_every_way_their_facts_name_them() -> None:
    turmeric = Material("Turmeric", "DYE", "Curcuma longa", ("haldi",))
    alum = Material("Alum", "MORDANT", None, ("fitkari",))
    water = Material("Water", "INPUT")
    agents = agent_materials([turmeric, water, alum])
    assert agents == [turmeric, alum]
    assert agent_names(agents) == ("Turmeric", "Curcuma longa", "haldi", "Alum", "fitkari")


def test_the_first_colour_a_token_depicts_is_the_one_drawn() -> None:
    assert first_depicted(["WHITE", "RED", "BLACK"], ["Madder", "Syahi"]) == ("RED", "madder")
    assert first_depicted(["WHITE"], ["Madder"]) is None
    assert specimen_token("madder") == "--dye-madder"


@pytest.mark.parametrize("token", RECORDED_FROM_THEIR_FACTS)
def test_each_specimen_recorded_from_a_craft_s_facts_is_found_from_its_own_material_and_quote(
    token: str,
) -> None:
    (record,) = [found for found in specimen_records() if found.token == specimen_token(token)]
    dossier = json.loads((DOSSIERS / f"{record.craft}.json").read_text(encoding="utf-8"))
    material = next(row for row in dossier["materials"] if row["id"] == record.material)
    names = [
        material["name"],
        *material.get("localNames", []),
        *filter(None, [material.get("botanicalName")]),
    ]
    colour = DEPICTED_COLOURS[token].colour
    assert depicted_material(colour, names) == token
    quotes = [
        quote["quote"] for row in dossier["claims"] if row["id"] in record.claims for quote in row["quotes"]
    ]
    assert any(states_colour(quote, colour) for quote in quotes), token
