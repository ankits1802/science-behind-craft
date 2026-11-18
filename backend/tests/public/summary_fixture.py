from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.research.citations import AnswerSentence, SourceRef
from app.research.craft_catalogue import CatalogueSummary
from app.research.craft_page_context import HeroImage
from app.research.crafts import CraftRef
from app.research.media_refs import MediaRef
from app.services.curation_keys import curated_id
from app.services.public_summary import CuratedReading, PublicSummaryRecords

__all__ = [
    "AJRAKH",
    "DHOKRA",
    "SUMMARY_GOLDEN",
    "TIKULI",
    "ajrakh_reading",
    "summary_fixture_records",
]

SUMMARY_GOLDEN = "public.summary.golden.json"
AJRAKH = "Kutch-Ajrakh"
DHOKRA = "Bastar-Dhokra"
TIKULI = "Tikuli-Painting"
CURATED_AT = "2026-11-17T18:17:00Z"


@dataclass(frozen=True)
class Quoted:
    source: str
    locator: str
    quote: str


@dataclass(frozen=True)
class Stated:
    key: str
    text: str
    quotes: tuple[Quoted, ...]


SOURCES: dict[str, dict[str, dict[str, Any]]] = {
    AJRAKH: {
        "S01": {
            "kind": "GI_JOURNAL",
            "title": "Geographical Indications Journal No. 188: Kutch Ajrakh, G.I. Application No. 1050",
            "authors": [],
            "year": 2023,
            "url": "https://search.ipindia.gov.in/IPOJournal/Journal/ViewJournal",
            "publisher": "Geographical Indications Registry, Government of India",
            "reliability": "A",
        },
        "S13": {
            "kind": "WEB_PAGE",
            "title": "Ajrakh: An Introduction",
            "authors": ["Mushtak Khan"],
            "year": None,
            "url": "https://www.sahapedia.org/ajrakh-introduction-0",
            "publisher": "Sahapedia",
            "reliability": "B",
        },
        "S15": {
            "kind": "WEB_PAGE",
            "title": "Ajrakh: Rhythm of Blues",
            "authors": ["Ruchira Ghose", "Mushtak Khan", "Kritika Narula"],
            "year": None,
            "url": "https://artsandculture.google.com/story/WAWhhiXYIwIA8A",
            "publisher": "Crafts Museum, New Delhi, on Google Arts & Culture",
            "reliability": "B",
        },
        "S20": {
            "kind": "OTHER",
            "title": "Water woes: Kutch's age-old Ajrakh craft faces its nemesis, once again",
            "authors": ["Azera Parveen Rahman"],
            "year": 2019,
            "url": "https://india.mongabay.com/2019/10/water-woes-kutchs-age-old-ajrakh-craft-faces-its-nemesis-once-again/",
            "publisher": "Mongabay India",
            "reliability": "C",
        },
    },
    DHOKRA: {
        "S03": {
            "kind": "GI_JOURNAL",
            "title": "Geographical Indications Journal No. 24",
            "authors": [],
            "year": 2008,
            "url": "https://ipindia.nic.in/girindia/journal/24.pdf",
            "publisher": "Geographical Indications Registry, Government of India",
            "reliability": "A",
        },
        "S15": {
            "kind": "WEB_PAGE",
            "title": "Dhokra Shilp: The Bell Metal Craft of Bastar",
            "authors": ["Palash Vaswani"],
            "year": None,
            "url": "https://dsource.in/resource/dhokra-shilp",
            "publisher": "D'source, Industrial Design Centre, IIT Bombay",
            "reliability": "B",
        },
    },
    TIKULI: {
        "S02": {
            "kind": "GOVERNMENT_REPORT",
            "title": "Design and Technology Development Workshop for Tikuli Art at Tikuli Cluster Danapur",
            "authors": ["Hema Vishwakarma"],
            "year": 2022,
            "url": "https://umsas.org.in/wp-content/uploads/2022/01/03-DTDW-Report-Tikuli-Art-Hema-Vishwakarma.pdf",
            "publisher": "Upendra Maharathi Shilp Anusandhan Sansthan",
            "reliability": "A",
        },
        "S19": {
            "kind": "OTHER",
            "title": "Tikuli Painting in Bihar: History, Technique and the Revival",
            "authors": ["Athmaja Biju"],
            "year": 2025,
            "url": "https://www.abirpothi.com/tikuli-painting-in-bihar-history-technique-and-the-revival/",
            "publisher": "Abirpothi",
            "reliability": "C",
        },
    },
}

AJRAKH_CLAIMS = (
    Stated(
        "C001",
        "Kutch Ajrakh is an elaborate resist block-printing technique built on a series of direct and resist "
        "printing and dyeing steps.",
        (
            Quoted(
                "S01",
                "Application 1050, specification and description, p. 6",
                "Kutch Ajrakh is an elaborate resist block printing technique that involves series of direct and "
                "resist printing and dyeing to create unique effects.",
            ),
            Quoted(
                "S15",
                "Introduction",
                "Ajrakh is a unique combination of hand block printing and resist dyeing.",
            ),
        ),
    ),
    Stated(
        "C022",
        "In 2001 an earthquake that caused severe damage in Kutch almost destroyed Dhamadka.",
        (
            Quoted(
                "S13",
                "paragraph 13",
                "In 2001, an earthquake which caused severe damage in Kutch almost destroyed the village of Dhamadka.",
            ),
        ),
    ),
    Stated(
        "C023",
        "After the 2001 earthquake the block printers of Dhamadka moved 40 km away, in search of good quality "
        "groundwater, to a new village named Ajrakhpur.",
        (
            Quoted(
                "S01",
                "Application 1050, geographical area of production, p. 8",
                "After a massive earthquake in Kutch in 2001, the block printers were forced to relocate. They "
                "settled in Ajrakhpur village.",
            ),
            Quoted(
                "S20",
                "section 'History repeats itself'",
                "moved from their earlier settlement in Dhamadka to their present location, 40 km away, in search "
                "of good quality groundwater",
            ),
        ),
    ),
)

DHOKRA_CLAIMS = (
    Stated(
        "C006",
        "Dhokra products are cast in bell metal by the lost wax process and show a finish of bell metal wire work.",
        (
            Quoted(
                "S03",
                "lines 1114-1116",
                "Dhokra products are cast in bell metal by lost wax process and display an intriguing finish having "
                "bell metal wire work",
            ),
        ),
    ),
    Stated(
        "C007",
        "In Bastar, Dhokra is made by the Ghadwa community.",
        (
            Quoted(
                "S15", "lines 28-29", "Dhokra shilp is widely practiced by the Ghadwa community of Bastar."
            ),
        ),
    ),
)

TIKULI_CLAIMS = (
    Stated(
        "C001",
        "Tikuli is the local word in Bihar for the bindi, the bright dot that women wear on the forehead.",
        (
            Quoted(
                "S02",
                "p. 5",
                "The word 'tikuli' is the local term for 'bindi', which is usually a bright, colorful dot that "
                "women wear between their brows.",
            ),
        ),
    ),
    Stated(
        "C003",
        "Modern tikuli painting uses glossy enamel paints on hardboard or medium-density fibreboard.",
        (
            Quoted(
                "S19",
                "para 2",
                "Modern Tikuli practice shifts from glass to hardboard or medium-density fibreboard and uses enamel "
                "paints that produce a glossy, durable surface.",
            ),
        ),
    ),
)


def summary_fixture_records() -> PublicSummaryRecords:
    readings = {AJRAKH: ajrakh_reading(), DHOKRA: dhokra_reading(), TIKULI: tikuli_reading()}
    return PublicSummaryRecords(
        counts=CatalogueSummary(crafts=420, gi_registered=209, states=33, placed=401, families=9, kinds=36),
        reader_slugs=frozenset((*readings, "Kutch-Bandhani", "Madhubani-Paintings", "Agra-Marble-Inlay")),
        curated_slugs=frozenset(readings),
        points=(
            _point(
                "state-10",
                "Bihar",
                25.6,
                85.1,
                [(TIKULI, "Tikuli Painting"), ("Madhubani-Paintings", "Madhubani Paintings")],
            ),
            _point("state-22", "Chhattisgarh", 21.3, 81.9, [(DHOKRA, "Bastar Dhokra")]),
            _point(
                "state-24",
                "Gujarat",
                22.7,
                71.6,
                [
                    ("Kutch-Bandhani", "Kutch Bandhani"),
                    (AJRAKH, "Kutch Ajrakh"),
                    ("Stone-Others", "Stone Others"),
                ],
            ),
            _point("district-449", "Kachchh", 23.7, 69.8, [(AJRAKH, "Kutch Ajrakh")]),
            _point("state-9", "Uttar Pradesh", 26.9, 80.9, [("Stone-Others", "Stone Others")]),
        ),
        readings=readings,
    )


def ajrakh_reading() -> CuratedReading:
    lede = _sentence(AJRAKH, "pa1.1", AJRAKH_CLAIMS[0].text, AJRAKH_CLAIMS[:1])
    history = _sentence(
        AJRAKH,
        "pa2.1",
        "In 2001 an earthquake almost destroyed Dhamadka, and its block printers moved 40 km away, in search of "
        "good quality groundwater, to a new village named Ajrakhpur.",
        AJRAKH_CLAIMS[1:],
    )
    hero = _hero(
        AJRAKH,
        "Ajrak_Craft_artisan.jpeg",
        "An ajrakh artisan from Kutch holding up a printed ajrakh with its central field and borders",
        "Visdaviva",
    )
    return _reading(AJRAKH, "Kutch Ajrakh", None, hero=hero, lede=(lede,), sections=(history,))


def dhokra_reading() -> CuratedReading:
    lede = _sentence(
        DHOKRA,
        "pd1.1",
        "Bastar Dhokra is bell metal cast by the lost wax process and finished with bell metal wire work, made in "
        "Bastar by the Ghadwa community.",
        DHOKRA_CLAIMS,
    )
    hero = _hero(
        DHOKRA,
        "AT_WORKSHOP.jpg",
        "Working on a figure at a workshop in Kondagaon, Bastar (2006)",
        "Sushilsakhuja",
    )
    return _reading(DHOKRA, "Bastar Dhokra", "Ghadwa kala", hero=hero, lede=(lede,), sections=())


def tikuli_reading() -> CuratedReading:
    lede = _sentence(
        TIKULI,
        "pt1.1",
        "Tikuli is the local word in Bihar for the bindi, and tikuli painting is now made with glossy enamel paints "
        "on hardboard or MDF board.",
        TIKULI_CLAIMS,
    )
    return _reading(TIKULI, "Tikuli Painting", "Tikuli", hero=None, lede=(lede,), sections=())


def _reading(
    slug: str,
    name: str,
    local_name: str | None,
    *,
    hero: HeroImage | None,
    lede: tuple[AnswerSentence, ...],
    sections: tuple[AnswerSentence, ...],
) -> CuratedReading:
    sources = {
        str(curated_id(slug, key)): SourceRef.model_validate(
            {"id": str(curated_id(slug, key)), "doi": None, "licence": None, "attribution": None, **source}
        )
        for key, source in SOURCES[slug].items()
    }
    return CuratedReading(
        craft=CraftRef(slug=slug, name=name, path=f"/crafts/{slug}"),
        local_name=local_name,
        hero=hero,
        lede=lede,
        sentences=(*lede, *sections),
        sources=sources,
    )


def _point(
    key: str, name: str, latitude: float, longitude: float, crafts: list[tuple[str, str]]
) -> dict[str, Any]:
    listed = [{"slug": slug, "name": label, "path": f"/crafts/{slug}"} for slug, label in crafts]
    return {
        "key": key,
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "total": len(listed),
        "crafts": listed,
    }


def _sentence(slug: str, sentence_id: str, text: str, claims: tuple[Stated, ...]) -> AnswerSentence:
    citations = [
        {
            "id": str(curated_id(slug, "quote", stated.key, quoted.source)),
            "claimId": str(curated_id(slug, stated.key)),
            "sourceId": str(curated_id(slug, quoted.source)),
            "quote": quoted.quote,
            "locator": quoted.locator,
            "context": None,
            "evidence": "QUOTED",
            "level": "PROVISIONAL",
        }
        for stated in claims
        for quoted in stated.quotes
    ]
    return AnswerSentence.model_validate(
        {"id": sentence_id, "text": text, "level": "PROVISIONAL", "citations": citations}
    )


def _hero(slug: str, file: str, caption: str, author: str) -> HeroImage:
    media = MediaRef.model_validate(
        {
            "id": str(curated_id(slug, "picture", file)),
            "display": "INLINE",
            "provider": "curation",
            "pageUrl": f"https://commons.wikimedia.org/wiki/File:{file}",
            "imageUrl": f"https://upload.wikimedia.org/wikipedia/commons/{file}",
            "width": None,
            "height": None,
            "title": caption,
            "alt": caption,
            "author": author,
            "site": "commons.wikimedia.org",
            "credit": None,
            "licence": "CC BY-SA 3.0",
            "licenceUrl": "https://creativecommons.org/licenses/by-sa/3.0/",
            "sourceId": None,
            "retrievedAt": CURATED_AT,
        }
    )
    return HeroImage(media=media, caption=caption)
