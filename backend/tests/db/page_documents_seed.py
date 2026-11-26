import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ArticleSection,
    Claim,
    ClaimSource,
    Concept,
    Craft,
    CraftCategory,
    CraftSubCategory,
    CuratedCraft,
    KnowledgePiece,
    KnowledgePieceSubject,
    MediaRef,
    Source,
    User,
)
from app.services.curated_index import CuratedPage

__all__ = [
    "ADMIN",
    "ALUM",
    "BARE_SLUG",
    "CATEGORY_CLAIM",
    "CATEGORY_SLUG",
    "CONCEPT_PLAYER",
    "CRAFT",
    "CRAFT_CLAIM",
    "CRAFT_PLAYER",
    "CRAFT_SLUG",
    "CRAFT_TEXT",
    "FAMILY_CLAIM",
    "FAMILY_SLUG",
    "OTHER_CRAFTS_PLAYER",
    "PICTURE",
    "seed",
]

NOW = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)
CRAFT = uuid.UUID("9d0c0000-0000-4000-8000-000000000001")
FAMILY = uuid.UUID("9d0c0000-0000-4000-8000-000000000002")
BARE = uuid.UUID("9d0c0000-0000-4000-8000-000000000003")
CATEGORY = uuid.UUID("9d0c0000-0000-4000-8000-000000000004")
SUB_CATEGORY = uuid.UUID("9d0c0000-0000-4000-8000-000000000005")
ALUM = uuid.UUID("9d0c0000-0000-4000-8000-000000000006")
PAPER = uuid.UUID("9d0c0000-0000-4000-8000-000000000007")
MEDIA = uuid.UUID("9d0c0000-0000-4000-8000-000000000008")
ADMIN = uuid.UUID("9d0c0000-0000-4000-8000-000000000009")
CRAFT_CLAIM = uuid.UUID("9d0c0000-0000-4000-8000-0000000000c1")
FAMILY_CLAIM = uuid.UUID("9d0c0000-0000-4000-8000-0000000000c2")
CATEGORY_CLAIM = uuid.UUID("9d0c0000-0000-4000-8000-0000000000c3")
CRAFT_SLUG = "Page-Docs-Test-Craft"
FAMILY_SLUG = "Page-Docs-Test-Family"
BARE_SLUG = "Page-Docs-Test-Bare"
CATEGORY_SLUG = "Page-Docs-Test-Category"
CRAFT_TEXT = "Alum fixes the madder red on the cotton."
PICTURE = "page-docs-test-craft/pictures/i01"
CRAFT_PLAYER = "page-docs-test-craft/chemistry/alum-player"
CONCEPT_PLAYER = "shared/chemistry/page-docs-alum-crystal"
OTHER_CRAFTS_PLAYER = "page-docs-test-bare/chemistry/alum-photo"
FOCAL = {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.6}


async def seed(session: AsyncSession) -> None:
    await _subjects(session)
    await _facts(session)
    await _sections(session)
    await _components(session)
    await _curated_picture(session)


async def _subjects(session: AsyncSession) -> None:
    session.add(
        User(id=ADMIN, email=f"admin-{uuid.uuid4().hex[:8]}@example.org", name="Layout Admin", role="ADMIN")
    )
    session.add(CraftCategory(id=CATEGORY, slug=CATEGORY_SLUG, name="Page Docs Test Category", sortOrder=990))
    await session.flush()
    session.add(
        CraftSubCategory(
            id=SUB_CATEGORY,
            slug="page-docs-test-sub",
            name="Page docs printing",
            categoryId=CATEGORY,
            sortOrder=1,
        )
    )
    await session.flush()
    session.add_all(_crafts())
    await session.flush()


def _crafts() -> list[Craft]:
    return [
        Craft(
            id=CRAFT,
            name="Page Docs Test Craft",
            slug=CRAFT_SLUG,
            subCategoryId=SUB_CATEGORY,
            stateOfPractice=["Madhya Pradesh"],
            giStatus="GI",
        ),
        Craft(
            id=FAMILY,
            name="Page Docs Test Family",
            slug=FAMILY_SLUG,
            subCategoryId=SUB_CATEGORY,
            isCatchAll=True,
        ),
        Craft(id=BARE, name="Page Docs Test Bare", slug=BARE_SLUG, subCategoryId=SUB_CATEGORY),
    ]


def _claim(claim_id: uuid.UUID, text: str) -> Claim:
    return Claim(
        id=claim_id,
        subjectType="CONCEPT",
        subjectId=ALUM,
        predicate="states",
        text=text,
        evidenceLevel="PROVISIONAL",
        origin="IMPORT",
        field="CHEMISTRY",
    )


async def _facts(session: AsyncSession) -> None:
    session.add(Concept(id=ALUM, craftId=CRAFT, type="MATERIAL", name="Alum"))
    session.add(
        Source(
            id=PAPER, kind="PAPER", title="Alum mordants on cotton", url="https://example.org/alum", year=2019
        )
    )
    await session.flush()
    session.add_all(
        [
            _claim(CRAFT_CLAIM, CRAFT_TEXT),
            _claim(FAMILY_CLAIM, "Printers across India print with carved wooden blocks."),
            _claim(CATEGORY_CLAIM, "Textile crafts dye, print and weave cloth."),
        ]
    )
    await session.flush()
    for n, claim_id in enumerate((CRAFT_CLAIM, FAMILY_CLAIM, CATEGORY_CLAIM), 1):
        session.add(
            ClaimSource(
                claimId=claim_id,
                sourceId=PAPER,
                quote=f"alum quote {n}",
                locator=f"p. {n}",
                quoteCheck="PASS",
            )
        )
    await session.flush()


def _section(field: str, claim_id: uuid.UUID, text: str, **subject: Any) -> ArticleSection:
    status = subject.pop("status", "PUBLISHED")
    sentences = [{"text": text, "claimIds": [str(claim_id)]}]
    return ArticleSection(field=field, version=1, status=status, sentences=sentences, **subject)


async def _sections(session: AsyncSession) -> None:
    session.add_all(
        [
            _section("CHEMISTRY", CRAFT_CLAIM, CRAFT_TEXT, craftId=CRAFT),
            _section("PROCESS", CRAFT_CLAIM, "The cloth is printed with an alum paste.", craftId=CRAFT),
            _section("GEOGRAPHY", CRAFT_CLAIM, "The river water rinses the printed cloth.", craftId=CRAFT),
            _section(
                "HISTORY", CRAFT_CLAIM, "A proposed history sentence.", craftId=CRAFT, status="PROPOSED"
            ),
            _section(
                "OVERVIEW",
                FAMILY_CLAIM,
                "Printers across India print with carved wooden blocks.",
                craftId=FAMILY,
            ),
            _section(
                "OVERVIEW", CATEGORY_CLAIM, "Textile crafts dye, print and weave cloth.", categoryId=CATEGORY
            ),
            _section("HISTORY", CRAFT_CLAIM, "A proposed bare sentence.", craftId=BARE, status="PROPOSED"),
        ]
    )
    await session.flush()


def _piece(label: str, craft_id: uuid.UUID | None) -> KnowledgePiece:
    return KnowledgePiece(
        craftId=craft_id,
        kind="reaction_player",
        facet="CHEMISTRY",
        topicKey=f"monograph:{label}",
        language="en",
        depth="EXPERT",
        payload={"monograph": "Page-Docs-Monograph", "anchor": "#fig2", "chapter": "chemistry", "units": []},
        claimIds=[CRAFT_CLAIM],
        sourceIds=[str(PAPER)],
        contentHash=uuid.uuid4().hex + uuid.uuid4().hex,
        label=label,
        title=f"Title of {label}",
        description="An alum player.",
        fields=["PROCESS"],
    )


async def _components(session: AsyncSession) -> None:
    own, shared = _piece(CRAFT_PLAYER, CRAFT), _piece(CONCEPT_PLAYER, None)
    others = _piece(OTHER_CRAFTS_PLAYER, BARE)
    session.add_all([own, shared, others])
    await session.flush()
    session.add_all(
        [
            KnowledgePieceSubject(pieceId=piece.id, kind="CONCEPT", conceptId=ALUM)
            for piece in (shared, others)
        ]
    )
    await session.flush()


async def _curated_picture(session: AsyncSession) -> None:
    session.add(
        MediaRef(
            id=MEDIA,
            urlKey=uuid.uuid4().hex + uuid.uuid4().hex,
            display="INLINE",
            provider="curation",
            pageUrl="https://commons.wikimedia.org/wiki/File:Page_docs.jpg",
            imageUrl="https://upload.wikimedia.org/wikipedia/commons/a/ab/Page_docs.jpg",
            width=1600,
            height=1200,
            title="A printed cloth",
            alt="A printed cloth",
            author="A. Printer",
            site="Wikimedia Commons",
            credit="A. Printer",
            licence="CC BY-SA 4.0",
            licenceUrl="https://creativecommons.org/licenses/by-sa/4.0/",
            retrievedAt=NOW,
        )
    )
    await session.flush()
    session.add(
        CuratedCraft(craftId=CRAFT, version=1, curatedAt=NOW, coverage="THIN", digest="0" * 64, page=_page())
    )
    await session.flush()


def _page() -> dict[str, Any]:
    picture = {
        "key": "I01",
        "mediaRefId": str(MEDIA),
        "caption": "A printed cloth held up",
        "stageKey": None,
        "claimIds": [str(CRAFT_CLAIM)],
        "placement": {"chapter": "glance", "role": "MASTHEAD"},
        "focal": FOCAL,
    }
    page = CuratedPage.model_validate(
        {
            "craftSlug": CRAFT_SLUG,
            "version": 1,
            "curatedAt": NOW.isoformat(),
            "coverage": "THIN",
            "searched": [],
            "processId": None,
            "craftConcepts": {},
            "overview": {},
            "conflicts": [],
            "openQuestions": [],
            "places": [],
            "communities": [],
            "stages": [],
            "materials": [],
            "tools": [],
            "reactions": [],
            "glossary": [],
            "pictures": [picture],
            "environment": [],
        }
    )
    return page.model_dump(mode="json", by_alias=True)
