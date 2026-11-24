import json
from pathlib import Path

from app.services.compose_held import About
from app.services.compose_molecule import molecule_3d
from app.services.document_components_data import kit_data

from .held import BAGRU, CONFORMER_SDF, FACTS, IRON_OXIDE, cited_claims, claim, delivery_problems

AJRAKH_CONTENT = (
    Path(__file__).resolve().parents[2] / "app" / "data" / "monographs" / "Kutch-Ajrakh" / "content.json"
)
CONFORMERS = {6293: CONFORMER_SDF, 62667: None}


def test_a_molecule_is_composed_from_a_compound_the_craft_s_materials_name_with_pubchem_s_conformer() -> None:
    result = molecule_3d(BAGRU, About(), CONFORMERS)
    assert result.composed
    (component,) = result.components
    body = component.proposal
    assert (body.kind, body.label) == ("molecule_3d", "bagru-print/chemistry/alizarin-3d")
    spec = body.spec
    assert spec is not None
    (model,) = spec["molecules"]
    assert (model["key"], model["cid"], model["name"]) == ("m6293", 6293, "Alizarin")
    assert model["formula"] == [
        "C",
        {"text": "14", "style": "sub"},
        "H",
        {"text": "8", "style": "sub"},
        "O",
        {"text": "4", "style": "sub"},
    ]
    assert model["atoms"].startswith("14 carbon, 8 hydrogen and 4 oxygen atoms.")
    assert [item["label"] for item in spec["key"]] == [
        "Carbon",
        "Hydrogen",
        "Oxygen, O",
        "3D conformers computed by PubChem.",
    ]
    assert body.units[spec["head"]["title"]].text == "Alizarin in three dimensions"
    assert delivery_problems(result.components) == []


def test_the_model_carries_the_geometry_the_page_turns_and_cites_only_the_craft_s_facts() -> None:
    (component,) = molecule_3d(BAGRU, About(), CONFORMERS).components
    spec = component.proposal.spec
    held = json.loads(AJRAKH_CONTENT.read_text(encoding="utf-8"))["data"]["mol-data"]["6293"]
    assert kit_data({}, "molecule_3d", spec) == {"mol-data": {"6293": held}}
    assert cited_claims(component) == {claim(9)}
    assert component.proposal.units[spec["side"][0]["unit"]].text == FACTS[claim(9)]


def test_a_compound_without_a_conformer_or_an_atom_colour_is_left_out_and_named() -> None:
    result = molecule_3d(BAGRU, About(), CONFORMERS)
    assert result.left_out == ("a 3D conformer for Potassium alum (CID 62667): PubChem holds none",)
    refused = molecule_3d(BAGRU, About(compound=62667), CONFORMERS)
    assert refused.components == () and refused.missing == result.left_out
    uncoloured = molecule_3d(BAGRU, About(compound=62667), {62667: IRON_OXIDE})
    assert uncoloured.missing == (
        "an atom colour for Fe in Potassium alum (CID 62667): the design system colours C, H, N and O only; "
        "ask the team for the others before a 3D model draws them",
    )


def test_a_molecule_about_a_compound_no_material_names_is_refused_with_its_reason() -> None:
    refused = molecule_3d(BAGRU, About(compound=5318432), CONFORMERS)
    assert refused.missing == (
        "the compound CID 5318432: no material of Bagru-Print is held as that compound",
    )
