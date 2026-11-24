import uuid
from dataclasses import replace
from typing import Any

from app.research.blocks import ProcessLadderBlock
from app.research.blocks_matter import MaterialCardBlock
from app.research.blocks_signature import MordantBathBlock
from app.research.citations import SourceRef
from app.research.monograph_document import MonographDocument
from app.services.document_components import DocumentStructure, StructureBlock, block_citations
from app.services.knowledge_view import ClaimView
from app.services.monograph_generated_assembly import assembled_document
from app.services.monograph_generated_drawings import Drawings

from .generated_parts import generated, source

KEY = "bagh-print/chemistry/colour-key"
PAPER = uuid.UUID("c0108000-0000-4000-8000-000000000301")
BLUE_FACT = uuid.UUID("c0108000-0000-4000-8000-000000000101")
WHY_FACT = uuid.UUID("c0108000-0000-4000-8000-000000000102")
YELLOW_FACT = uuid.UUID("c0108000-0000-4000-8000-000000000103")
STAGE_FACT = uuid.UUID("c0108000-0000-4000-8000-000000000104")
BLUE_QUOTE = "At first green, the cloth turns blue in the air."
WHY_TEXT = "Indigo oxidises to its blue form in the air."
YELLOW_QUOTE = "The marigold bath gives a bright yellow."
NAMESPACE = uuid.UUID("c0108000-0000-4000-8000-000000000000")
SHIFTS = (
    (
        uuid.UUID("c0108000-0000-4000-8000-000000000201"),
        "With an alum mordant, madder dyes cotton red.",
        "alum mordant, red",
    ),
    (
        uuid.UUID("c0108000-0000-4000-8000-000000000202"),
        "With an iron mordant, madder dyes cotton black.",
        "iron mordant, black",
    ),
    (
        uuid.UUID("c0108000-0000-4000-8000-000000000203"),
        "Marigold flowers give the cloth a yellow.",
        "the flowers give a deep yellow",
    ),
)


def citation(claim: uuid.UUID, quote: str) -> dict[str, Any]:
    return {
        "id": f"cite-{claim}",
        "claimId": str(claim),
        "sourceId": str(PAPER),
        "quote": quote,
        "locator": "p. 4",
        "context": None,
        "evidence": "QUOTED",
        "level": "PROVISIONAL",
    }


def sentence(sentence_id: str, claim: uuid.UUID, text: str, quote: str) -> dict[str, Any]:
    cited = [citation(claim, quote)]
    return {"id": sentence_id, "text": text, "level": "PROVISIONAL", "citations": cited, "terms": []}


def stage(
    ordinal: int, name: str, dye: str, after: tuple[str, list[str], uuid.UUID, str] | None
) -> dict[str, Any]:
    found: dict[str, Any] = {
        "stageId": str(uuid.uuid5(NAMESPACE, name)),
        "ordinal": ordinal,
        "name": name,
        "stageType": "DYE",
        "level": "PROVISIONAL",
        "sentences": [sentence(f"made.ladder.{ordinal}", STAGE_FACT, f"{name} is done in a bath.", "a bath")],
        "materials": [
            {
                "materialId": str(uuid.uuid5(NAMESPACE, dye)),
                "name": dye,
                "kind": "DYE",
                "role": "DYE",
                "citations": [citation(STAGE_FACT, "a bath")],
            }
        ],
        "conditions": [],
        "reactionIds": [],
    }
    if after is not None:
        text, colours, claim, quote = after
        found["after"] = {"text": text, "colours": colours, "citations": [citation(claim, quote)]}
    return found


BLUE_STAGE = stage(1, "Indigo dyeing", "Indigo", ("Blue in the air", ["BLUE"], BLUE_FACT, BLUE_QUOTE))
YELLOW_STAGE = stage(
    2, "Marigold dyeing", "Marigold", ("A bright yellow", ["YELLOW"], YELLOW_FACT, YELLOW_QUOTE)
)


def structure(*stages: dict[str, Any]) -> DocumentStructure:
    ladder = ProcessLadderBlock.model_validate(
        {
            "id": "made.ladder",
            "kind": "process_ladder",
            "version": 1,
            "reuse": None,
            "craft": {"slug": "Bagh-Print", "name": "Bagh Print", "path": "/crafts/Bagh-Print"},
            "processId": str(uuid.uuid5(NAMESPACE, "process")),
            "stages": list(stages),
        }
    )
    return structured({"made": [ladder]})


def structured(chapters: dict[str, list[Any]]) -> DocumentStructure:
    placed = {
        chapter: tuple(
            StructureBlock(
                f"bagh-print/blocks/{block.id.replace('.', '-')}",
                block,
                None,
                "A figure",
                "A figure.",
                *block_citations(block),
            )
            for block in blocks
        )
        for chapter, blocks in chapters.items()
    }
    ref = SourceRef.model_validate(
        {
            "id": str(PAPER),
            "kind": "PAPER",
            "title": "Dyeing notes",
            "authors": [],
            "year": 2021,
            "doi": None,
            "url": "https://example.org/dyeing",
            "publisher": None,
            "licence": None,
            "attribution": None,
            "reliability": "B",
        }
    )
    return DocumentStructure(trailing=placed, sources={str(PAPER): ref})


def fact(claim: uuid.UUID, text: str, quote: str) -> ClaimView:
    cited = [{"sourceId": str(PAPER), "quote": quote, "locator": "p. 4"}]
    return ClaimView(claim, text, "PROVISIONAL", "MATERIAL", None, citations=cited)


def keyed(shown: DocumentStructure, *hidden: uuid.UUID) -> MonographDocument:
    base = generated(components=(), pictures=())
    facts = {
        BLUE_FACT: fact(BLUE_FACT, "Indigo-dyed cloth turns blue in air.", BLUE_QUOTE),
        WHY_FACT: fact(WHY_FACT, WHY_TEXT, "indigo oxidises to its blue form"),
        YELLOW_FACT: fact(YELLOW_FACT, "Marigold dyes the cloth yellow.", YELLOW_QUOTE),
        **{claim: fact(claim, text, quote) for claim, text, quote in SHIFTS},
    }
    visible = {**base.visible, **{claim: view for claim, view in facts.items() if claim not in hidden}}
    sources = {**base.sources, str(PAPER): source("Dyeing notes", "https://example.org/dyeing")}
    built = assembled_document(replace(base, structure=shown, visible=visible, sources=sources), Drawings())
    assert built is not None
    return built


def text_of(document: MonographDocument, unit: str) -> str:
    return "".join(
        part if isinstance(part, str) else text_of_node(part) for part in document.content.units[unit].nodes
    )


def text_of_node(node: dict[str, Any]) -> str:
    return "".join(part if isinstance(part, str) else text_of_node(part) for part in node.get("c", []))


def with_why(found: dict[str, Any], text: str) -> dict[str, Any]:
    return {**found, "why": sentence("made.ladder.why1", WHY_FACT, text, "indigo oxidises to its blue form")}


def mordant_bath() -> MordantBathBlock:
    (alum, alum_text, alum_quote), (iron, iron_text, iron_quote), _ = SHIFTS
    swatches = [
        {
            "mordant": "alum",
            "colour": "red",
            "sentence": sentence("chem.bath.1", alum, alum_text, alum_quote),
        },
        {
            "mordant": "iron",
            "colour": "black",
            "sentence": sentence("chem.bath.2", iron, iron_text, iron_quote),
        },
    ]
    return MordantBathBlock.model_validate(
        {
            "id": "chem.figure-mordant-bath",
            "kind": "mordant_bath",
            "version": 1,
            "reuse": None,
            "dye": "madder",
            "fibre": "cotton",
            "swatches": swatches,
        }
    )


def flowers_card() -> MaterialCardBlock:
    flowers, flowers_text, flowers_quote = SHIFTS[2]
    return MaterialCardBlock.model_validate(
        {
            "id": "chem.card-1",
            "kind": "material_card",
            "version": 1,
            "reuse": None,
            "materialId": str(uuid.uuid5(NAMESPACE, "marigold")),
            "compoundId": None,
            "termKey": None,
            "name": "Marigold flowers",
            "materialKind": "DYE",
            "role": "DYE",
            "formula": None,
            "pubchemCid": None,
            "wikidataId": None,
            "localNames": [],
            "facts": [sentence("chem.card-1.1", flowers, flowers_text, flowers_quote)],
            "handling": [],
        }
    )


def mordants_and_a_dye() -> DocumentStructure:
    return structured({"chem": [mordant_bath(), flowers_card()]})
