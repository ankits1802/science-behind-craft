import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AdminDistrict,
    AdminState,
    Claim,
    ClaimSource,
    Concept,
    Craft,
    CraftCategory,
    CraftLocation,
    CraftSubCategory,
    CuratedCategoryClaim,
    KnowledgePiece,
    KnowledgePieceSubject,
    Source,
)

__all__ = [
    "CHAIN",
    "FARAWAY_SLUG",
    "METAL_SLUG",
    "METAL_WATER",
    "MONSOON",
    "NEIGHBOUR_SLUG",
    "RAINFALL",
    "TEXTILES_SLUG",
    "VAT",
    "seed",
]

GUJARAT, UTTAR_PRADESH = 24, 9
KACHCHH, AZAMGARH = 449, 123
TEXTILES = uuid.UUID("9e2b0000-0000-4000-8000-000000000001")
METAL = uuid.UUID("9e2b0000-0000-4000-8000-000000000002")
PRINTING = uuid.UUID("9e2b0000-0000-4000-8000-000000000003")
CASTING = uuid.UUID("9e2b0000-0000-4000-8000-000000000004")
HOME = uuid.UUID("9e2b0000-0000-4000-8000-000000000005")
NEIGHBOUR = uuid.UUID("9e2b0000-0000-4000-8000-000000000006")
FARAWAY = uuid.UUID("9e2b0000-0000-4000-8000-000000000007")
SMITH = uuid.UUID("9e2b0000-0000-4000-8000-000000000008")
HOME_DYE = uuid.UUID("9e2b0000-0000-4000-8000-000000000011")
HOME_CLIMATE = uuid.UUID("9e2b0000-0000-4000-8000-000000000012")
TEXTILE_DYE = uuid.UUID("9e2b0000-0000-4000-8000-000000000013")
WATER = uuid.UUID("9e2b0000-0000-4000-8000-000000000014")
PAPER = uuid.UUID("9e2b0000-0000-4000-8000-000000000020")
HOME_VAT = uuid.UUID("9e2b0000-0000-4000-8000-000000000021")
HOME_RAIN = uuid.UUID("9e2b0000-0000-4000-8000-000000000022")
TEXTILE_VAT = uuid.UUID("9e2b0000-0000-4000-8000-000000000023")
TEXTILE_WATER = uuid.UUID("9e2b0000-0000-4000-8000-000000000024")
METAL_WATER = uuid.UUID("9e2b0000-0000-4000-8000-000000000025")
TEXTILES_SLUG = "Held-Test-Textiles-Category"
METAL_SLUG = "Held-Test-Metal-Category"
HOME_SLUG = "Held-Test-Kachchh-Print"
NEIGHBOUR_SLUG = "Held-Test-Kachchh-Tie-Dye"
FARAWAY_SLUG = "Held-Test-Azamgarh-Print"
SMITH_SLUG = "Held-Test-Azamgarh-Bell-Metal"
VAT = "shared/chemistry/held-test-vat-dip"
CHAIN = "shared/chemistry/held-test-leaf-to-cloth"
RAINFALL = "shared/climate/held-test-kachchh-rainfall"
MONSOON = "shared/climate/held-test-kachchh-monsoon"
MONOGRAPH = "Held-Test-Monograph"


async def seed(session: AsyncSession) -> None:
    await _places(session)
    await _shelves(session)
    await _crafts(session)
    await _facts(session)
    await _pieces(session)


async def _places(session: AsyncSession) -> None:
    await session.merge(AdminState(lgd=GUJARAT, name="Gujarat"))
    await session.merge(AdminState(lgd=UTTAR_PRADESH, name="Uttar Pradesh"))
    await session.flush()
    await session.merge(AdminDistrict(lgd=KACHCHH, stateLgd=GUJARAT, name="Kachchh"))
    await session.merge(AdminDistrict(lgd=AZAMGARH, stateLgd=UTTAR_PRADESH, name="Azamgarh"))
    await session.flush()


async def _shelves(session: AsyncSession) -> None:
    session.add_all(
        [
            CraftCategory(id=TEXTILES, slug=TEXTILES_SLUG, name="Held Test Textiles", sortOrder=993),
            CraftCategory(id=METAL, slug=METAL_SLUG, name="Held Test Metal", sortOrder=994),
        ]
    )
    await session.flush()
    session.add_all(
        [
            CraftSubCategory(
                id=PRINTING, slug="held-test-printing", name="Printing", categoryId=TEXTILES, sortOrder=1
            ),
            CraftSubCategory(
                id=CASTING, slug="held-test-casting", name="Casting", categoryId=METAL, sortOrder=1
            ),
        ]
    )
    await session.flush()


async def _crafts(session: AsyncSession) -> None:
    crafts = (
        (HOME, HOME_SLUG, PRINTING, "Gujarat", KACHCHH),
        (NEIGHBOUR, NEIGHBOUR_SLUG, PRINTING, "Gujarat", KACHCHH),
        (FARAWAY, FARAWAY_SLUG, PRINTING, "Uttar Pradesh", AZAMGARH),
        (SMITH, SMITH_SLUG, CASTING, "Uttar Pradesh", AZAMGARH),
    )
    session.add_all(
        Craft(
            id=craft_id,
            slug=slug,
            name=slug.replace("-", " "),
            subCategoryId=shelf,
            stateOfPractice=[state],
        )
        for craft_id, slug, shelf, state, _ in crafts
    )
    await session.flush()
    session.add_all(
        CraftLocation(
            id=uuid.uuid4(),
            craftId=craft_id,
            precision="DISTRICT",
            districtLgd=district,
            evidenceLevel="PROVISIONAL",
        )
        for craft_id, _, _, _, district in crafts
    )
    await session.flush()


def _claim(claim_id: uuid.UUID, concept_id: uuid.UUID, text: str, field: str) -> Claim:
    return Claim(
        id=claim_id,
        subjectType="CONCEPT",
        subjectId=concept_id,
        predicate="states",
        text=text,
        evidenceLevel="PROVISIONAL",
        origin="IMPORT",
        field=field,
    )


async def _facts(session: AsyncSession) -> None:
    session.add_all(
        [
            Concept(id=HOME_DYE, craftId=HOME, type="MATERIAL", name="Held test indigo"),
            Concept(id=HOME_CLIMATE, craftId=HOME, type="ENVIRONMENTAL_CONDITION", name="Held test monsoon"),
            Concept(id=TEXTILE_DYE, type="MATERIAL", name="Held test vat dye"),
            Concept(id=WATER, type="MATERIAL", name="Held test water"),
            Source(id=PAPER, kind="PAPER", title="Vats and rain", url="https://example.org/vats", year=2021),
        ]
    )
    await session.flush()
    facts = (
        (
            HOME_VAT,
            HOME_DYE,
            "The printers' cloth leaves the vat green and turns blue in the air.",
            "CHEMISTRY",
        ),
        (HOME_RAIN, HOME_CLIMATE, "The printers' district gets most of its rain in three months.", "CLIMATE"),
        (TEXTILE_VAT, TEXTILE_DYE, "Indigo is reduced to a soluble leuco form in the vat.", "CHEMISTRY"),
        (TEXTILE_WATER, WATER, "Dyers rinse cloth in running water.", "CHEMISTRY"),
        (METAL_WATER, WATER, "Casters quench hot bronze in water.", "CHEMISTRY"),
    )
    session.add_all(_claim(claim_id, concept, text, field) for claim_id, concept, text, field in facts)
    await session.flush()
    session.add_all(
        ClaimSource(claimId=claim_id, sourceId=PAPER, quote=text[:20], locator="p. 3", quoteCheck="PASS")
        for claim_id, _, text, _ in facts
    )
    session.add_all(
        CuratedCategoryClaim(claimId=claim_id, categoryId=category, key=key, discipline="CHEMISTRY")
        for claim_id, category, key in (
            (TEXTILE_VAT, TEXTILES, "C001"),
            (TEXTILE_WATER, TEXTILES, "C002"),
            (METAL_WATER, METAL, "C001"),
        )
    )
    await session.flush()


def _piece(label: str, kind: str, facet: str, title: str, claims: list[uuid.UUID]) -> KnowledgePiece:
    return KnowledgePiece(
        craftId=None,
        kind=kind,
        facet=facet,
        topicKey=f"monograph:{label}",
        language="en",
        depth="EXPERT",
        payload={"monograph": MONOGRAPH, "anchor": None, "chapter": "why", "units": []},
        claimIds=claims,
        sourceIds=[str(PAPER)],
        contentHash=uuid.uuid4().hex + uuid.uuid4().hex,
        label=label,
        title=title,
        description=f"{title}, drawn from the printers' records.",
        fields=[],
    )


async def _pieces(session: AsyncSession) -> None:
    vat = _piece(VAT, "dip_player", "CHEMISTRY", "Green from the Kachchh vat", [HOME_VAT, TEXTILE_VAT])
    chain = _piece(CHAIN, "diagram", "CHEMISTRY", "Where the blue comes from", [HOME_VAT])
    rainfall = _piece(RAINFALL, "chart", "CLIMATE", "Annual rainfall", [HOME_RAIN])
    monsoon = _piece(MONSOON, "chart", "CLIMATE", "Monsoon months in Kachchh", [HOME_RAIN])
    session.add_all([vat, chain, rainfall, monsoon])
    await session.flush()
    session.add_all(
        [
            KnowledgePieceSubject(pieceId=vat.id, kind="CRAFT", craftId=HOME),
            KnowledgePieceSubject(pieceId=chain.id, kind="CONCEPT", conceptId=WATER),
            KnowledgePieceSubject(pieceId=rainfall.id, kind="PLACE", placeKey=f"lgd:{KACHCHH}"),
        ]
    )
    await session.flush()
