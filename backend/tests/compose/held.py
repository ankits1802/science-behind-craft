import dataclasses
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.research.component_specs_general_delivery import spec_problems, unit_problems
from app.research.page_proposals import PageComponent
from app.services.compose_held import (
    CraftHeld,
    HeldAfter,
    HeldCompound,
    HeldFact,
    HeldMaterial,
    HeldReaction,
    HeldSpecies,
    HeldStage,
    HeldTiming,
)

__all__ = [
    "AJRAKH_FACT",
    "ALIZARIN",
    "BAGRU",
    "CONFORMER_SDF",
    "FACTS",
    "FERROUS_SULPHATE",
    "IRON_OXIDE",
    "IRON_SULPHATE",
    "SILICA",
    "SLUG",
    "cited_claims",
    "claim",
    "delivery_problems",
    "held",
    "molfile",
    "unrecorded",
    "with_syahi_as",
]

SLUG = "Bagru-Print"
NAME = "Bagru Print"
CONFORMER_SDF = (
    Path(__file__).resolve().parents[1] / "sources" / "fixtures" / "pubchem_conformer.sdf"
).read_text(encoding="ascii")
Atom = tuple[str, float, float, float]


def molfile(cid: int, atoms: Iterable[Atom], bonds: Iterable[tuple[int, int, int]]) -> str:
    placed = [
        f"{x:10.4f}{y:10.4f}{z:10.4f} {symbol:<3} 0  0  0  0  0  0  0  0  0  0  0  0"
        for symbol, x, y, z in atoms
    ]
    joined = [f"{first:3d}{second:3d}{order:3d}  0  0  0  0" for first, second, order in bonds]
    counts = f"{len(placed):3d}{len(joined):3d}  0     0  0  0  0  0  0999 V2000"
    return "\n".join([str(cid), "  -OEChem-11172610523D", "", counts, *placed, *joined, "M  END", "$$$$"])


IRON_OXIDE = molfile(14974, [("Fe", 0.0, 0.0, 0.0), ("O", 1.6, 0.0, 0.0)], [(1, 2, 2)])
SILICA = molfile(
    24261, [("O", -1.6, 0.0, 0.0), ("Si", 0.0, 0.0, 0.0), ("O", 1.6, 0.0, 0.0)], [(1, 2, 2), (2, 3, 2)]
)
FERROUS_SULPHATE = molfile(
    24393,
    [
        ("S", 0.0, 0.0, 0.0),
        ("O", 1.5, 0.0, 0.0),
        ("O", -1.5, 0.0, 0.0),
        ("O", 0.0, 1.5, 0.0),
        ("O", 0.0, -1.5, 0.0),
        ("Fe", 3.5, 0.0, 0.0),
    ],
    [(1, 2, 1), (1, 3, 2), (1, 4, 2), (1, 5, 1), (2, 6, 1)],
)


def claim(number: int) -> uuid.UUID:
    return uuid.UUID(f"ba900000-0000-4000-8000-{number:012d}")


HARDA_AFTER, SYAHI, BLACK, ALUM_RED, RED_AFTER, BATH_TIME, WASH_AFTER = (claim(n) for n in range(1, 8))
HARDA, MADDER, SUBSTITUTE, POMEGRANATE, ALUM, YELLOW_AFTER, TURMERIC = (claim(n) for n in range(8, 15))
AJRAKH_FACT = uuid.UUID("aa000000-0000-4000-8000-000000000099")
FACTS = {
    HARDA_AFTER: "After the harda bath the cloth turns yellow.",
    SYAHI: "Syahi is made from scrap iron and acetic acid, which give iron(II) acetate and hydrogen.",
    BLACK: "Printed syahi reacts with the tannin of harda and the cloth turns black where it is printed.",
    ALUM_RED: "In the madder bath alizarin binds the aluminium of the printed alum and gives red.",
    RED_AFTER: "After the madder bath the cloth is red where alum was printed and black where syahi was.",
    BATH_TIME: "The cloth is boiled in the madder bath for an hour and a half.",
    WASH_AFTER: "Washing in running water leaves the ground pale.",
    HARDA: "Harda, the fruit of the myrobalan tree, gives the cloth its tannin.",
    MADDER: "Madder root holds alizarin, the dye of the red.",
    SUBSTITUTE: "Synthetic alizarin now often stands in for madder root.",
    POMEGRANATE: "Pomegranate rind can take the place of harda.",
    ALUM: "Alum is printed where the cloth will be red.",
    YELLOW_AFTER: "After the yellow dyeing the cloth is yellow from turmeric and pomegranate rind.",
    TURMERIC: "Turmeric, haldi, is rubbed on for the yellow.",
}
ALIZARIN = HeldCompound(6293, "Alizarin", "C14H8O4")
POTASSIUM_ALUM = HeldCompound(62667, "Potassium alum", "KAl(SO4)2·12H2O")
IRON_SULPHATE = HeldCompound(24393, "Ferrous sulphate", "FeSO4")
YELLOW_STAGE = HeldStage(
    "S06",
    "Yellow dyeing",
    "DYE",
    (YELLOW_AFTER,),
    ("M08", "M06"),
    HeldAfter("Yellow from turmeric and pomegranate rind", ("YELLOW",), YELLOW_AFTER),
)
TURMERIC_DYE = HeldMaterial(
    "M08", "Turmeric", "DYE", (TURMERIC,), role="DYE", local_names=("haldi",), botanical_name="Curcuma longa"
)


def _stages() -> tuple[HeldStage, ...]:
    return (
        HeldStage(
            "S01",
            "Harda",
            "MORDANT",
            (HARDA,),
            ("M01",),
            HeldAfter("Yellow", ("YELLOW",), HARDA_AFTER, ("--dye-harda",)),
        ),
        HeldStage("S02", "Syahi", "PREP", (SYAHI,)),
        HeldStage("S03", "Black printing", "PRINT", (BLACK,), ("M05",)),
        HeldStage(
            "S04",
            "Madder bath",
            "DYE",
            (RED_AFTER,),
            ("M03", "M02"),
            HeldAfter(
                "Red where alum was printed, black where syahi was",
                ("RED", "BLACK"),
                RED_AFTER,
                ("--dye-madder",),
            ),
            HeldTiming("an hour and a half", BATH_TIME),
        ),
        HeldStage(
            "S05", "Washing", "WASH", (WASH_AFTER,), ("M07",), HeldAfter("Pale", ("WHITE",), WASH_AFTER)
        ),
    )


def _materials() -> tuple[HeldMaterial, ...]:
    return (
        HeldMaterial(
            "M01",
            "Harda",
            "MORDANT",
            (HARDA,),
            None,
            ("--dye-harda",),
            (("M06", POMEGRANATE),),
            role="MORDANT",
        ),
        HeldMaterial("M02", "Alum", "MORDANT", (ALUM,), POTASSIUM_ALUM, ("--dye-lime",), role="MORDANT"),
        HeldMaterial(
            "M03", "Madder", "DYE", (MADDER,), ALIZARIN, ("--dye-madder",), (("M04", SUBSTITUTE),), role="DYE"
        ),
        HeldMaterial("M04", "Synthetic alizarin", "DYE", (SUBSTITUTE,), ALIZARIN, role="DYE"),
        HeldMaterial("M05", "Syahi", "MORDANT", (SYAHI,), None, ("--dye-kut",), role="MORDANT"),
        HeldMaterial("M06", "Pomegranate rind", "DYE", (POMEGRANATE,), role="DYE", local_names=("naspal",)),
        HeldMaterial("M07", "Water", "WATER", (WASH_AFTER,), role="INPUT"),
    )


def _reactions() -> tuple[HeldReaction, ...]:
    iron = (HeldSpecies("iron", "Fe"), HeldSpecies("acetic acid", "CH3COOH"))
    acetate = (HeldSpecies("iron(II) acetate", "Fe(CH3COO)2"), HeldSpecies("hydrogen", "H2"))
    return (
        HeldReaction(
            "R01",
            "COMPLEXATION",
            "S03",
            (HeldSpecies("syahi"), HeldSpecies("tannin")),
            (HeldSpecies("black"),),
            (BLACK,),
        ),
        HeldReaction(
            "R02",
            "COMPLEXATION",
            "S04",
            (HeldSpecies("alizarin"), HeldSpecies("aluminium")),
            (HeldSpecies("red"),),
            (ALUM_RED, AJRAKH_FACT),
        ),
        HeldReaction(
            "R03", "REDOX", "S04", (HeldSpecies("leucoindigo"),), (HeldSpecies("indigo"),), (AJRAKH_FACT,)
        ),
        HeldReaction("R04", "REDOX", "S02", iron, acetate, (SYAHI,), (1, 2, 1, 1)),
    )


def held(**changes: Any) -> CraftHeld:
    found = {
        "slug": SLUG,
        "name": NAME,
        "facts": {claim_id: HeldFact(claim_id, text) for claim_id, text in FACTS.items()},
        "stages": _stages(),
        "materials": _materials(),
        "reactions": _reactions(),
    }
    return CraftHeld(**(found | changes))


BAGRU = held()


def _unrecorded(stage: HeldStage) -> HeldStage:
    return (
        stage
        if stage.after is None
        else dataclasses.replace(stage, after=dataclasses.replace(stage.after, tokens=()))
    )


def unrecorded(*extra: HeldStage) -> CraftHeld:
    stages = tuple(_unrecorded(stage) for stage in (*_stages(), YELLOW_STAGE, *extra))
    materials = tuple(dataclasses.replace(material, tokens=()) for material in (*_materials(), TURMERIC_DYE))
    return held(stages=stages, materials=materials)


def with_syahi_as(compound: HeldCompound) -> CraftHeld:
    materials = tuple(
        dataclasses.replace(material, compound=compound) if material.key == "M05" else material
        for material in _materials()
    )
    return held(materials=materials)


def cited_claims(component: PageComponent) -> set[uuid.UUID]:
    return {claim_id for unit in component.proposal.units.values() for claim_id in unit.claim_ids}


def delivery_problems(components: Iterable[PageComponent], craft: CraftHeld = BAGRU) -> list[str]:
    cited = {claim_id: [fact.text] for claim_id, fact in craft.facts.items()}
    problems: list[str] = []
    for component in components:
        body = component.proposal
        assert body.spec is not None
        problems += spec_problems(body.kind, body.spec, body.units)
        problems += unit_problems(body.units, cited)
    return problems
