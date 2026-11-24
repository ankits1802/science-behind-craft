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
    "IRON_OXIDE",
    "SLUG",
    "cited_claims",
    "claim",
    "delivery_problems",
    "held",
]

SLUG = "Bagru-Print"
NAME = "Bagru Print"
CONFORMER_SDF = (
    Path(__file__).resolve().parents[1] / "sources" / "fixtures" / "pubchem_conformer.sdf"
).read_text(encoding="ascii")
IRON_OXIDE = "\n".join(
    [
        "14974",
        "  -OEChem-11172610523D",
        "",
        "  2  1  0     0  0  0  0  0  0999 V2000",
        "    0.0000    0.0000    0.0000 Fe  0  0  0  0  0  0  0  0  0  0  0  0",
        "    1.6000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0",
        "  1  2  2  0  0  0  0",
        "M  END",
        "$$$$",
    ]
)


def claim(number: int) -> uuid.UUID:
    return uuid.UUID(f"ba900000-0000-4000-8000-{number:012d}")


HARDA_AFTER, SYAHI, BLACK, ALUM_RED, RED_AFTER, BATH_TIME, WASH_AFTER = (claim(n) for n in range(1, 8))
HARDA, MADDER, SUBSTITUTE, POMEGRANATE, ALUM = (claim(n) for n in range(8, 13))
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
}
ALIZARIN = HeldCompound(6293, "Alizarin", "C14H8O4")
POTASSIUM_ALUM = HeldCompound(62667, "Potassium alum", "KAl(SO4)2·12H2O")


def _stages() -> tuple[HeldStage, ...]:
    return (
        HeldStage(
            "S01", "Harda", "MORDANT", (HARDA,), ("M01",), HeldAfter("Yellow", ("yellow",), HARDA_AFTER)
        ),
        HeldStage("S02", "Syahi", "PREP", (SYAHI,)),
        HeldStage("S03", "Black printing", "PRINT", (BLACK,), ("M05",)),
        HeldStage(
            "S04",
            "Madder bath",
            "DYE",
            (RED_AFTER,),
            ("M03", "M02"),
            HeldAfter("Red where alum was printed, black where syahi was", ("red", "black"), RED_AFTER),
            HeldTiming("an hour and a half", BATH_TIME),
        ),
        HeldStage(
            "S05", "Washing", "WASH", (WASH_AFTER,), ("M07",), HeldAfter("Pale", ("white",), WASH_AFTER)
        ),
    )


def _materials() -> tuple[HeldMaterial, ...]:
    return (
        HeldMaterial("M01", "Harda", "MORDANT", (HARDA,), None, ("--dye-harda",), (("M06", POMEGRANATE),)),
        HeldMaterial("M02", "Alum", "MORDANT", (ALUM,), POTASSIUM_ALUM, ("--dye-lime",)),
        HeldMaterial("M03", "Madder", "DYE", (MADDER,), ALIZARIN, ("--dye-madder",), (("M04", SUBSTITUTE),)),
        HeldMaterial("M04", "Synthetic alizarin", "DYE", (SUBSTITUTE,), ALIZARIN),
        HeldMaterial("M05", "Syahi", "MORDANT", (SYAHI,), None, ("--dye-kut",)),
        HeldMaterial("M06", "Pomegranate rind", "DYE", (POMEGRANATE,)),
        HeldMaterial("M07", "Water", "WATER", (WASH_AFTER,)),
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
