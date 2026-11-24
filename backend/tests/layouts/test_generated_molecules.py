import dataclasses
from pathlib import Path

from app.research.component_specs_general_delivery import DeliveredComponent, DeliveredUnit
from app.services.compose_held import About
from app.services.compose_molecule import molecule_3d
from app.services.monograph_generated_assembly import assembled_document
from app.services.monograph_generated_drawings import Drawings

from ..compose.held import BAGRU, CONFORMER_SDF
from .generated_parts import ALUM, TEXT_ALUM, component, generated

LABEL = "bagh-print/chemistry/alizarin-3d"


def delivered_molecule() -> DeliveredComponent:
    (composed,) = molecule_3d(BAGRU, About(), {6293: CONFORMER_SDF}).components
    spec = composed.proposal.spec
    assert spec is not None
    units = {
        ref: DeliveredUnit(
            text=TEXT_ALUM if unit.claim_ids else unit.text, claim_ids=[ALUM] if unit.claim_ids else []
        )
        for ref, unit in composed.proposal.units.items()
    }
    return DeliveredComponent(spec=spec, units=units)


def test_a_delivered_molecule_brings_its_own_turned_model_to_the_generated_page(tmp_path: Path) -> None:
    delivery = delivered_molecule()
    molecule = dataclasses.replace(component(LABEL, monograph=None), kind="molecule_3d", delivered=delivery)
    built = assembled_document(generated(components=(molecule,)), Drawings(root=tmp_path))
    assert built is not None
    geometry = delivery.spec["molecules"][0]["geometry"]
    assert built.content.data["mol-data"] == {
        "6293": {"atoms": geometry["atoms"], "bonds": geometry["bonds"], "R": geometry["radius"], "marks": []}
    }
    assert built.specs[LABEL]["molecules"][0]["drawing"]["children"][0]["attrs"] == {"class": "mol-g"}


def test_a_molecule_drawn_without_its_geometry_brings_no_model(tmp_path: Path) -> None:
    delivery = delivered_molecule()
    model = {key: value for key, value in delivery.spec["molecules"][0].items() if key != "geometry"}
    still = DeliveredComponent(spec={**delivery.spec, "molecules": [model]}, units=delivery.units)
    molecule = dataclasses.replace(component(LABEL, monograph=None), kind="molecule_3d", delivered=still)
    built = assembled_document(generated(components=(molecule,)), Drawings(root=tmp_path))
    assert built is not None and "mol-data" not in built.content.data
