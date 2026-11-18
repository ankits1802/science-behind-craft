from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

NAMESPACE = uuid.UUID("7e57a1d0-3010-4000-8000-000000000000")


def uid(name: str) -> str:
    return str(uuid.uuid5(NAMESPACE, name))


def source(
    name: str,
    kind: str,
    title: str,
    *,
    url: str | None = None,
    year: int | None = None,
    doi: str | None = None,
    publisher: str | None = None,
    authors: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "id": uid(f"source/{name}"),
        "kind": kind,
        "title": title,
        "authors": list(authors),
        "year": year,
        "doi": doi,
        "url": url,
        "publisher": publisher,
        "licence": None,
        "attribution": None,
        "reliability": "B",
    }


GI_COPY = source(
    "gi-copy",
    "GI_JOURNAL",
    "Geographical Indications Journal No. 188 (19 Dec 2023), G.I. Application No. 1050 - Kutch Ajrakh "
    "(journal copy)",
    url="https://search.ipindia.gov.in/GIRPublicSearch/Application/Details/1050",
    year=2023,
    publisher="Geographical Indications Registry, Chennai (IP India)",
)
GI_JOURNAL = source(
    "gi-journal",
    "GI_JOURNAL",
    "Geographical Indications Journal No. 188: Kutch Ajrakh, G.I. Application No. 1050",
    url="https://search.ipindia.gov.in/IPOJournal/Journal/ViewJournal?FileName=ipo-docs%2FJournal_188.pdf",
    year=2023,
    publisher="Geographical Indications Registry, Government of India",
)
FRATER_WEB = source(
    "frater-web",
    "WEB_PAGE",
    "Indigo in Kutch, India: Art and Science, Environment and Economics (essay in Blue Gold: The Art "
    "and Science of Indigo)",
    url="https://publications.mingei.org/blue-gold/essays/essay-4-fra-sc/",
    year=2025,
    publisher="Mingei International Museum, San Diego",
)
FRATER_BOOK = source(
    "frater-book",
    "BOOK_CHAPTER",
    "Indigo in Kutch, India: Art and Science, Environment and Economics (Blue Gold: The Art and Science "
    "of Indigo)",
    url="https://publications.mingei.org/blue-gold/essays/essay-4-fra-sc",
    year=2024,
    publisher="Mingei International Museum",
    authors=("Judy Frater",),
)
KHAMIR_PART = source(
    "khamir-part",
    "WEB_PAGE",
    "Ajrakh exhibition, Part 2: The art of Ajrakh",
    url="https://exhibitions-khamir.org/ajrakh/art-of-ajrakh",
    publisher="Khamir",
)
KHAMIR_ART = source(
    "khamir-art",
    "WEB_PAGE",
    "Art of Ajrakh (Ajrakh exhibition)",
    url="https://www.exhibitions-khamir.org/ajrakh/art-of-ajrakh/",
    publisher="Khamir",
)
EDWARDS = source(
    "edwards",
    "PAPER",
    "Ajrakh: From Caste Dress to Catwalk",
    url="https://irep.ntu.ac.uk/id/eprint/29181/1/PubSub6671_Edwards.pdf",
    year=2016,
    doi="10.1080/00404969.2016.1211436",
    publisher="Textile History, Pasold Research Fund",
)
EDWARDS_JOURNAL = source(
    "edwards-journal",
    "PAPER",
    "Ajrakh: from caste dress to catwalk",
    url="https://www.tandfonline.com/doi/full/10.1080/00404969.2016.1211436",
    year=2016,
    doi="https://doi.org/10.1080/00404969.2016.1211436",
    publisher="Textile History",
)
FRONTIERS = source(
    "frontiers",
    "WEB_PAGE",
    "Microbial Communities Associated With Indigo Fermentation That Thrive in Anaerobic Alkaline "
    "Environments",
    url="https://www.frontiersin.org/journals/microbiology/articles/10.3389/fmicb.2018.02196/full",
    year=2018,
)
DOWN_TO_EARTH = source(
    "dte",
    "WEB_PAGE",
    "Dyeing cotton fabrics is an ancient Indian art",
    url="https://www.downtoearth.org.in/amp/story/environment/dyeing-cotton-fabrics-is-an-ancient-indian-art",
    year=1992,
)
MET = source(
    "met",
    "WEB_PAGE",
    "Indian Block-Printed Textiles: Past and Present",
    url="https://www.metmuseum.org/perspectives/indian-block-printed-textiles",
    year=2016,
)
IJTK = source(
    "ijtk",
    "PAPER",
    "Ajarkh, the resist printed fabric of Gujarat",
    url="https://nopr.niscpr.res.in/bitstream/123456789/578/1/IJTK.pdf",
    year=2008,
)
IMPART = source("impart", "ENCYCLOPEDIA", "Ajrakh", url="https://imp-art.org/articles/ajrakh/", year=2022)
VAM = source(
    "vam",
    "WEB_PAGE",
    "Ajrakh process sample, IS.7:1 to 3-2007 (made by Ismail Mohammad Khatri, Ajrakhpur, 2006)",
    url="https://collections.vam.ac.uk/item/O132500/",
    year=2007,
)
PUBCHEM_INDIGO = source(
    "pubchem-indigo",
    "COMPOUND_RECORD",
    "Indigo (PubChem CID 10215)",
    url="https://pubchem.ncbi.nlm.nih.gov/compound/10215",
)
BAGRU_GI = source(
    "bagru-gi",
    "GI_JOURNAL",
    "Form GI-1: Application for Registration of a Geographical Indication, Bagru Hand Block Print",
    url="https://origin-gi.com/wp-content/uploads/2017/01/129-bagru-hand-block-print.pdf",
    year=2009,
)
OTHER_CRAFTS = source(
    "other-crafts",
    "WEB_PAGE",
    "Printed and dyed textiles of Rajasthan and Andhra",
    url="https://crafts.example.org/printed-textiles",
)
INDUS = source(
    "indus",
    "PAPER",
    "Some Iconic Textile Craft of Hand Block Prints in India",
    url="https://doi.org/10.29121/granthaalayah.v10.i3.2022.4546",
    year=2022,
)
SOURCES = (
    GI_COPY,
    GI_JOURNAL,
    FRATER_WEB,
    FRATER_BOOK,
    KHAMIR_PART,
    KHAMIR_ART,
    EDWARDS,
    EDWARDS_JOURNAL,
    FRONTIERS,
    DOWN_TO_EARTH,
    MET,
    IJTK,
    IMPART,
    VAM,
    PUBCHEM_INDIGO,
    BAGRU_GI,
    OTHER_CRAFTS,
    INDUS,
)


@dataclass(frozen=True)
class Claim:
    key: str
    text: str
    sources: tuple[dict[str, Any], ...]

    @property
    def id(self) -> str:
        return uid(f"claim/{self.key}")

    def citations(self) -> list[dict[str, Any]]:
        return [
            {
                "id": uid(f"citation/{self.key}/{n}"),
                "claimId": self.id,
                "sourceId": cited["id"],
                "quote": self.text.rstrip("."),
                "locator": None,
                "context": None,
                "evidence": "QUOTED",
                "level": "PROVISIONAL",
            }
            for n, cited in enumerate(self.sources)
        ]


def sentence(sentence_id: str, text: str, *claims: Claim) -> dict[str, Any]:
    citations = [citation for claim in claims for citation in claim.citations()]
    return {"id": sentence_id, "text": text, "level": "PROVISIONAL", "citations": citations, "terms": []}


def stated(sentence_id: str, claim: Claim) -> dict[str, Any]:
    return sentence(sentence_id, claim.text, claim)


VAT_SOLUBLE = Claim(
    "vat-soluble",
    "Indigo is not soluble in water whereas leucoindigo is; indigo is transformed to leucoindigo by "
    "indigo-reducing bacteria.",
    (FRONTIERS,),
)
INDIGO_WHITE = Claim(
    "indigo-white",
    "Indigo is reduced to soluble 'indigo white' for dyeing and fixed to the fibre by air oxidation.",
    (DOWN_TO_EARTH,),
)
FERMENTED = Claim(
    "fermented",
    "Natural indigo is fermented with lime, dates and soda, while synthetic indigo often has 'Hydros' added.",
    (GI_COPY,),
)
NAAND = Claim(
    "naand",
    "Stage 8 dyes the cloth in indigo for 10 to 15 minutes, traditionally in a naand dug into the ground.",
    (IJTK,),
)
GREEN_BLUE = Claim(
    "green-blue",
    "Cloth lifted from the indigo vat is bright green at first and turns blue as oxygen meets the dye.",
    (IMPART, GI_JOURNAL),
)
OXIDISES = Claim(
    "oxidises",
    "After the resist-printed fabric is immersed in the indigo vat, the dye oxidises to the insoluble "
    "blue form in air.",
    (MET,),
)
NATURAL_OR_GERMAN = Claim(
    "natural-or-german",
    "Indigo can be natural (Indigofera tinctoria) or synthetic 'German' indigo; natural indigo is "
    "fermented in the vat.",
    (GI_COPY,),
)
SHIKARPUR = Claim(
    "shikarpur", "Indigo came from Shikarpur in Sindh and was also grown in Dhamadka.", (KHAMIR_PART,)
)
DHAMADKA_GROWN = Claim(
    "dhamadka-grown", "In Dhamadka a small amount of indigo was grown while the river was active.", (GI_COPY,)
)
AJRAKH_INDIGO = Claim(
    "ajrakh-indigo",
    "Ajrakh indigo is either natural indigo from the plant Indigofera tinctoria or a synthesised "
    "substitute known as German indigo.",
    (GI_JOURNAL,),
)
CONFINED = Claim(
    "confined",
    "Indigofera tinctoria, once cultivated on a vast commercial scale in India, is now confined to a few "
    "areas.",
    (EDWARDS,),
)
COLOURS = Claim("colours", "Ajrakh colours come from indigo, madder and iron acetate.", (FRATER_WEB,))
COLOURS_BOOK = Claim(
    "colours-book",
    "Indigo supplies the blue of Kutch Ajrakh, beside madder for red and iron acetate for black.",
    (FRATER_BOOK,),
)
LIME_RESIST = Claim(
    "lime-resist",
    "Contemporary ajrakh uses a resist of lime, which is calcium hydroxide, and gum from the babul tree.",
    (EDWARDS_JOURNAL, KHAMIR_ART),
)
IRON_SPOTS = Claim(
    "iron-spots",
    "Even one percent of iron in the wash water leaves black spots on pale yellow, myrobalan-dyed cloth.",
    (KHAMIR_PART,),
)
MORNING_WASH = Claim(
    "morning-wash",
    "The final wash is usually done early in the morning, because warm afternoon water may dissolve alum.",
    (GI_JOURNAL,),
)
REVERTS = Claim(
    "reverts",
    "After the fabric is dipped in the vat and exposed to air, indigo white reverts into insoluble indigo.",
    (DOWN_TO_EARTH,),
)
BLOCKS_CAKES = Claim(
    "blocks-cakes",
    "Natural indigo is bought in blocks or cakes, ground to a powder and soaked before it is fermented.",
    (GI_COPY,),
)
TWO_SHADES = Claim(
    "two-shades",
    "For two shades of blue the cloth is reprinted between immersions in the indigo vat.",
    (GI_COPY,),
)
IMMERSED = Claim(
    "immersed",
    "The cloth is immersed in indigo for the blue areas, and the resist is then washed off.",
    (VAM,),
)
KHAVDA = Claim(
    "khavda",
    "In Kachchh, ajrakh was mainly produced in the villages of Khavda and Dhamadka.",
    (KHAMIR_PART,),
)
INDUS_LINK = Claim(
    "indus-link",
    "One account links the history of the Ajrakh of Kutch and Sindh to the Indus valley civilization.",
    (INDUS,),
)
BAGRU_NIL = Claim(
    "bagru-nil",
    "Indigo blue (nil) is extracted from Indigofera tinctoria; synthetic indigo granules are also used.",
    (BAGRU_GI,),
)
DABU_INDIGO = Claim("dabu-indigo", "Traditional Dabu uses natural dyes such as indigo.", (OTHER_CRAFTS,))
SANGANER_INDIGO = Claim(
    "sanganer-indigo", "A Sanganer cotton of about 1850 uses indigo for its blue.", (OTHER_CRAFTS,)
)
ALUM_MORDANT = Claim("alum-mordant", "Alum is used as a mordant to fasten the colours.", (GI_COPY,))
BAGRU_ALUM = Claim(
    "bagru-alum",
    "Post-mordanting with diluted alum (fitkari) in a big copper vessel makes the yellow dye fast.",
    (BAGRU_GI,),
)
ALIZARIN_1868 = Claim(
    "alizarin-1868",
    "Alizarin, first synthesised in 1868 by Graebe and Liebermann, superseded madder.",
    (GI_COPY,),
)
BAGH_ALIZARIN = Claim(
    "bagh-alizarin", "Alizarin is made from the root bark of aal for Bagh prints.", (OTHER_CRAFTS,)
)
COTTON_COUNT = Claim(
    "cotton-count",
    "Artisans procure cotton fabric from 60s to 120s count depending on its end use.",
    (GI_COPY,),
)
KACHCHH_FINER = Claim(
    "kachchh-finer",
    "Ajrakh is printed in Kachchh and in Barmer, and the Kachchh cloths are finer.",
    (GI_JOURNAL,),
)
