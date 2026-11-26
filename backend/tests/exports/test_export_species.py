from app.research.component_specs_kit import SpeciesPart
from app.services.export_still_kit import kit_scene_parts, part_still, scene_still
from app.services.export_still_kit_species import species_boxes

MADDER = (0x7E, 0x03, 0x2C)
INK_1 = (0x1C, 0x18, 0x15)


def species(role: str, material: str | None = None, breaks: bool = False) -> SpeciesPart:
    return SpeciesPart(part="species", role=role, material=material, breaks=breaks, label="u0001")


def test_the_reactants_stand_before_the_arrow_and_the_products_after_it_in_the_scene_s_frame() -> None:
    two_to_one = [species("reactant"), species("reagent"), species("product")]
    assert species_boxes(two_to_one) == [(16.0, 4.0, 72.0), (16.0, 84.0, 72.0), (140.0, 32.0, 96.0)]
    three_to_one = [species("reactant"), species("reactant"), species("reagent"), species("product")]
    assert species_boxes(three_to_one)[:3] == [(0.0, 28.0, 48.0), (56.0, 28.0, 48.0), (0.0, 84.0, 48.0)]


def test_a_species_scene_still_draws_each_bead_in_its_material_with_the_arrow_between() -> None:
    parts = kit_scene_parts(
        {
            "parts": [
                {"part": "species", "role": "reactant", "material": "--dye-madder", "label": "u0001"},
                {"part": "species", "role": "product", "label": "u0002"},
            ],
            "motion": "react",
        }
    )
    assert parts is not None
    still = scene_still(parts)
    assert (still.width, still.height) == (240, 160)
    assert sum(path.fill == MADDER for path in still.paths) == 1
    assert any(path.line == INK_1 and not path.closed and path.points[0] == (110, 80) for path in still.paths)


def test_a_bond_breaks_across_its_bead_and_an_unrecorded_colour_draws_as_an_outline() -> None:
    broken = part_still(species("reactant", "--dye-madder", breaks=True))
    plain = part_still(species("reactant", "--dye-madder"))
    assert len(broken.paths) == len(plain.paths) + 2
    outline = part_still(species("product"))
    assert all(path.fill != MADDER for path in outline.paths)
