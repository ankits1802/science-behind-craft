from __future__ import annotations

from typing import Any

from app.research.explainer import Explainer, ExplainerSection

from .indigo_blocks import (
    AJRAKH,
    ELEGANCE,
    FERMENTED_SAID,
    GITAGGED,
    INSTAGRAM,
    ITOKRI,
    JIOMART,
    NAAND_SAID,
    PINTEREST,
    VAT_PHOTO,
    ZAVERI,
    card,
    graph,
    ladder,
    molecule,
    pictures,
    prose,
    seat,
    supply,
    zoom,
)
from .indigo_claims import (
    AJRAKH_INDIGO,
    BLOCKS_CAKES,
    COLOURS,
    COLOURS_BOOK,
    CONFINED,
    DHAMADKA_GROWN,
    FERMENTED,
    GREEN_BLUE,
    IMMERSED,
    INDIGO_WHITE,
    INDUS_LINK,
    IRON_SPOTS,
    KACHCHH_FINER,
    KHAVDA,
    LIME_RESIST,
    MORNING_WASH,
    NAAND,
    NATURAL_OR_GERMAN,
    OXIDISES,
    REVERTS,
    SHIKARPUR,
    SOURCES,
    VAT_SOLUBLE,
    uid,
)

NATURAL_INDIGO = "Indigo (natural Indigofera tinctoria or synthetic)"
IN_THE_VAT = (VAT_SOLUBLE, INDIGO_WHITE, OXIDISES, GREEN_BLUE, NAAND)


def chemistry() -> list[dict[str, Any]]:
    return [
        prose(
            "s1.b1",
            (
                "Indigo itself does not dissolve in water, but leucoindigo does, made so by bacteria.",
                (VAT_SOLUBLE,),
            ),
            ("For dyeing, indigo is reduced to a soluble form called 'indigo white'.", (INDIGO_WHITE,)),
            (FERMENTED_SAID, (FERMENTED,)),
            (NAAND_SAID, (NAAND,)),
            ("Lifted from the vat, the cloth is bright green and turns blue in the air.", (GREEN_BLUE,)),
        ),
        card(
            "s1.b3",
            NATURAL_INDIGO,
            "indigo-natural",
            NATURAL_OR_GERMAN,
            SHIKARPUR,
            DHAMADKA_GROWN,
            *IN_THE_VAT,
        ),
        card("s1.b4", "Indigo", "indigo", AJRAKH_INDIGO, CONFINED, NATURAL_OR_GERMAN, *IN_THE_VAT),
        card("s1.b5", "Water", "water", IRON_SPOTS, VAT_SOLUBLE, MORNING_WASH),
        molecule("s1.b6"),
        graph("s1.b7", alizarin=False),
        pictures("s1.b8", (ITOKRI, (GREEN_BLUE,)), (ZAVERI, (GREEN_BLUE, VAT_SOLUBLE))),
    ]


def process() -> list[dict[str, Any]]:
    return [
        ladder("s2.b1"),
        prose(
            "s2.b2",
            ("Kutch Ajrakh is an elaborate resist block-printing craft of many stages.", (KACHCHH_FINER,)),
            (NAAND_SAID, (NAAND,)),
            (FERMENTED_SAID, (FERMENTED,)),
            ("In the vat, indigo becomes soluble indigo white, or leucoindigo.", (INDIGO_WHITE, VAT_SOLUBLE)),
            ("Exposed to air, the dye turns to its insoluble blue form on the fibre.", (OXIDISES,)),
            (
                "After the cloth is immersed in indigo for the blue areas, the resist is washed off.",
                (IMMERSED,),
            ),
        ),
        pictures("s2.b3", (ZAVERI, (NAAND,)), (JIOMART, (NAAND,))),
    ]


def materials() -> list[dict[str, Any]]:
    return [
        prose(
            "s3.b1",
            ("The indigo used in Kutch Ajrakh is either natural or German indigo.", (AJRAKH_INDIGO,)),
            (FERMENTED_SAID, (FERMENTED,)),
            ("Indigo itself is not soluble in water, but leucoindigo is.", (VAT_SOLUBLE,)),
            ("Alongside indigo, ajrakh colours also come from madder and iron acetate.", (COLOURS,)),
        ),
        supply("s3.b2"),
        card(
            "s3.b3", "Indigo (natural Indigofera tinctoria or synthetic)", "indigo-natural", NATURAL_OR_GERMAN
        ),
        card("s3.b4", "Indigo", "indigo", AJRAKH_INDIGO, CONFINED),
        card("s3.b5", "Lime", "lime", LIME_RESIST, NATURAL_OR_GERMAN),
        seat(
            "s3.b6",
            "CHEMIST",
            ("Indigo is not soluble in water but leucoindigo is.", VAT_SOLUBLE),
            ("Exposed to air, indigo white reverts into insoluble indigo.", REVERTS),
        ),
        seat(
            "s3.b7",
            "BOTANIST",
            (AJRAKH_INDIGO.text, AJRAKH_INDIGO),
            ("Ajrakh colours come from madder too.", COLOURS),
        ),
        seat("s3.b8", "MATERIALS_SCIENTIST", ("In air the dye oxidises to its blue form.", OXIDISES)),
        seat("s3.b9", "TECHNOLOGIST", (BLOCKS_CAKES.text, BLOCKS_CAKES)),
        zoom("s3.b10"),
        molecule("s3.b11"),
        graph("s3.b12", alizarin=True),
        pictures(
            "s3.b13",
            (ITOKRI, (AJRAKH_INDIGO,)),
            (INSTAGRAM, (AJRAKH_INDIGO,)),
            (ZAVERI, (AJRAKH_INDIGO,)),
            (VAT_PHOTO, (FERMENTED, VAT_SOLUBLE)),
        ),
    ]


def botany() -> list[dict[str, Any]]:
    return [
        prose(
            "s4.b1",
            ("Indigo supplies the blue of Kutch Ajrakh, beside madder and iron acetate.", (COLOURS_BOOK,)),
            ("The indigo used in Kutch Ajrakh is either natural or German indigo.", (AJRAKH_INDIGO,)),
            (FERMENTED_SAID, (FERMENTED,)),
            ("This fermentation matters because indigo does not dissolve in water.", (VAT_SOLUBLE,)),
            ("Indigofera tinctoria now grows only in a few areas of India.", (CONFINED,)),
        )
    ]


def history() -> list[dict[str, Any]]:
    return [
        prose(
            "s5.b1",
            ("Kutch Ajrakh is an elaborate resist block-printing craft of many stages.", (KACHCHH_FINER,)),
            ("Ajrakh was mainly made in Khavda and Dhamadka.", (KHAVDA,)),
            (COLOURS.text, (COLOURS,)),
            (INDUS_LINK.text, (INDUS_LINK,)),
            ("Lime and babul gum make the resist of contemporary ajrakh.", (LIME_RESIST,)),
        ),
        pictures("s5.b2", (GITAGGED, (KHAVDA,)), (ELEGANCE, (KHAVDA,)), (PINTEREST, (KHAVDA,))),
    ]


SECTIONS = (
    ("s1", "CHEMISTRY", "The chemistry", chemistry),
    ("s2", "PROCESS", "How it is made", process),
    ("s3", "MATERIALS", "Materials", materials),
    ("s4", "BOTANY", "Botany", botany),
    ("s5", "HISTORY", "History", history),
)


def recorded_sections() -> list[dict[str, Any]]:
    return [
        {
            "id": section_id,
            "discipline": discipline,
            "title": title,
            "order": order,
            "state": "READY",
            "blocks": blocks(),
            "searched": None,
        }
        for order, (section_id, discipline, title, blocks) in enumerate(SECTIONS, 1)
    ]


def recorded_indigo() -> Explainer:
    sections = [ExplainerSection.model_validate(section) for section in recorded_sections()]
    cited = dict.fromkeys(sid for section in sections for b in section.blocks for sid in b.cited_source_ids())
    by_id = {ref["id"]: ref for ref in SOURCES}
    return Explainer.model_validate(
        {
            "schemaVersion": 1,
            "answerId": uid("answer/indigo"),
            "question": "How does indigo turn blue on Kutch Ajrakh cloth?",
            "understood": {"crafts": [AJRAKH], "candidates": [], "depth": "EXPERT", "language": "en"},
            "sections": [section.model_dump(mode="json", by_alias=True) for section in sections],
            "sources": [by_id[source_id] for source_id in cited],
            "followUps": [],
            "createdAt": "2026-11-18T10:00:00Z",
        }
    )
