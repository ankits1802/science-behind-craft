import json
import uuid
from functools import cache
from typing import Any

from app.curation.files import CURATION_DIR
from app.research.blocks_lede import LedeBlock
from app.research.blocks_signature import SignatureBlock
from app.research.crafts import CraftRef
from app.research.term_marking import GlossaryEntry, TermMarker
from app.science.records import CompoundRecord
from app.services.answer_events import CitedClaims
from app.services.claim_seed import load_seed_claims, seed_id
from app.services.compound_lookup import record_source_id
from app.services.curation_keys import curated_id
from app.services.curation_rows import claim_source_id
from app.services.knowledge_view import ClaimView
from app.services.section_blocks import KeptSentence, lede_block
from app.services.section_enrichment import Enrichment, EnrichmentTools
from app.services.signature_blocks import (
    CraftCompounds,
    FiguredLede,
    SignatureFigures,
    ranked_facts,
    signature_block,
)
from app.services.signature_rules import FigureEvidence

__all__ = [
    "AJRAKH",
    "AJRAKH_REF",
    "DHOKRA",
    "FIRING_CLAIMS",
    "GOLDEN_QUESTION",
    "INDIGO_CID",
    "INDIGO_CLAIMS",
    "LOST_WAX_CLAIMS",
    "MORDANT_CLAIMS",
    "NIZAMABAD",
    "ajrakh_compounds",
    "built_figures",
    "curated_view",
    "dossier_claims",
    "enrichment",
    "evidence",
    "figure_of",
    "figured_lede",
    "plain_lede",
    "seed_view",
    "source_ref",
]

AJRAKH = "Kutch-Ajrakh"
DHOKRA = "Bastar-Dhokra"
NIZAMABAD = "Nizamabad-Black-Pottery"
INDIGO_CID = 10215
LOST_WAX_CLAIMS = ("C010", "C048", "C092", "C062", "C072")
FIRING_CLAIMS = ("C033", "C090")
MORDANT_CLAIMS = ("C080", "C093", "C078", "C075", "C082", "C072", "C055", "C041", "C095")
INDIGO_CLAIMS = (
    "C086",
    "C083",
    "C084",
    "C085",
    "C087",
    "seed-3965c8f733d2c1a997d5",
    "seed-a16a0906bd1fa81c6de0",
    "seed-d9b4aea0626d66ccdb60",
    "seed-86fcd25c654d7a0e0079",
    "seed-bdce98b16440ad986190",
)


@cache
def dossier_claims(slug: str) -> dict[str, dict[str, Any]]:
    dossier = json.loads((CURATION_DIR / f"{slug}.json").read_text(encoding="utf-8"))
    return {claim["id"]: claim for claim in dossier["claims"]}


@cache
def _seed_rows() -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in load_seed_claims()["claims"]}


def curated_view(slug: str, key: str) -> ClaimView:
    claim = dossier_claims(slug)[key]
    claim_id = curated_id(slug, key)
    level = "HYPOTHESIS" if claim.get("hypothesis") else "PROVISIONAL"
    citations = [
        {
            "id": str(claim_source_id(slug, key, quote["sourceId"], quote["quote"])),
            "claimId": str(claim_id),
            "sourceId": str(curated_id(slug, quote["sourceId"])),
            "quote": quote["quote"],
            "locator": quote.get("locator"),
            "context": None,
            "evidence": "QUOTED",
            "level": level,
        }
        for quote in claim["quotes"]
    ]
    return ClaimView(claim_id, claim["text"], level, "MECHANISM", None, citations=citations)


def seed_view(key: str) -> ClaimView:
    row = _seed_rows()[key]
    claim_id = seed_id("claim", key)
    level = row["evidenceLevel"]
    citations = [
        {
            "id": str(seed_id("claim-source", f"{key}:{index}")),
            "claimId": str(claim_id),
            "sourceId": str(seed_id("source", cite["sourceId"])),
            "quote": cite.get("quote"),
            "locator": cite.get("locator"),
            "context": None,
            "evidence": "QUOTED" if cite.get("quote") else "INFERRED",
            "level": level,
        }
        for index, cite in enumerate(row.get("sources") or [])
    ]
    return ClaimView(claim_id, row["text"], level, "MECHANISM", None, citations=citations)


def evidence(slug: str, keys: tuple[str, ...]) -> CitedClaims:
    views = [seed_view(key) if key.startswith("seed-") else curated_view(slug, key) for key in keys]
    sources = {
        citation["sourceId"]: source_ref(citation["sourceId"])
        for view in views
        for citation in view.citations
    }
    return CitedClaims(views={view.id: view for view in views}, sources=sources)


def source_ref(source_id: str, *, kind: str = "BOOK", title: str | None = None) -> dict[str, Any]:
    return {
        "id": source_id,
        "kind": kind,
        "title": title or f"Source {source_id[:8]}",
        "authors": [],
        "year": None,
        "doi": None,
        "url": None,
        "publisher": None,
        "licence": None,
        "attribution": None,
        "reliability": None,
    }


def ajrakh_compounds() -> CraftCompounds:
    source = str(record_source_id(INDIGO_CID))
    indigo = CompoundRecord(
        id=seed_id("compound", "indigo"),
        name="Indigo",
        formula="C16H10N2O2",
        pubchem_cid=INDIGO_CID,
        source_id=uuid.UUID(source),
    )
    leucoindigo = CompoundRecord(
        id=seed_id("compound", "leucoindigo"), name="Leucoindigo", formula="C16H12N2O2", pubchem_cid=None
    )
    ref = source_ref(source, kind="COMPOUND_RECORD", title=f"Indigo (PubChem CID {INDIGO_CID})")
    return CraftCompounds((indigo, leucoindigo), {source: ref})


GOLDEN_QUESTION = "Explain how Ajrakh works from every angle: its history, geography, politics and chemistry."
GLOSSARY = (
    GlossaryEntry("gach", ("gach",)),
    GlossaryEntry("kut", ("kut", "kat")),
    GlossaryEntry("alum", ("alum",)),
    GlossaryEntry("madder", ("madder",)),
    GlossaryEntry("indigo", ("indigo",)),
)
LEDE_CLAIMS = ("C068", "C080")
AJRAKH_REF = CraftRef(slug=AJRAKH, name="Kutch Ajrakh", path=f"/crafts/{AJRAKH}")


def figure_of(
    kind: str, slug: str, keys: tuple[str, ...], found: CraftCompounds | None = None
) -> SignatureBlock:
    held = found or CraftCompounds()
    block = signature_block(
        kind, FigureEvidence(ranked_facts(evidence(slug, keys)), held.compounds, held.sources)
    )
    assert block is not None, kind
    return block


def built_figures() -> list[SignatureBlock]:
    return [
        figure_of("indigo_vat", AJRAKH, INDIGO_CLAIMS, ajrakh_compounds()),
        figure_of("mordant_bath", AJRAKH, MORDANT_CLAIMS),
        figure_of("lost_wax", DHOKRA, LOST_WAX_CLAIMS),
        figure_of("firing", NIZAMABAD, FIRING_CLAIMS),
    ]


def enrichment() -> Enrichment:
    async def no_glossary(craft: CraftRef) -> list[GlossaryEntry]:
        return []

    async def no_pictures(ask: Any) -> None:
        return None

    tools = EnrichmentTools(glossary=no_glossary, pictures=no_pictures)
    return Enrichment(marker=TermMarker(GLOSSARY), tools=tools, craft_name=AJRAKH_REF.name)


def plain_lede(question: str = GOLDEN_QUESTION) -> LedeBlock:
    cited = evidence(AJRAKH, LEDE_CLAIMS)
    kept = [KeptSentence(view.text, (view.id,), (), False) for view in cited.views.values()]
    return enrichment().marked(lede_block(question, kept, cited))


async def figured_lede(
    lede: LedeBlock, *, question: str = GOLDEN_QUESTION, keys: tuple[str, ...] = MORDANT_CLAIMS
) -> FiguredLede:
    figures = SignatureFigures(compounds=_compounds_of)
    return await figures.figured(
        lede,
        question=question,
        craft=AJRAKH_REF,
        evidence=evidence(AJRAKH, (*LEDE_CLAIMS, *keys)),
        enrichment=enrichment(),
    )


async def _compounds_of(craft: CraftRef) -> CraftCompounds:
    return ajrakh_compounds()
