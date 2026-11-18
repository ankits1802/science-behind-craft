from __future__ import annotations

from typing import Any

from .indigo_claims import (
    AJRAKH_INDIGO,
    ALIZARIN_1868,
    ALUM_MORDANT,
    BAGH_ALIZARIN,
    BAGRU_ALUM,
    BAGRU_NIL,
    CONFINED,
    COTTON_COUNT,
    DABU_INDIGO,
    DHAMADKA_GROWN,
    GREEN_BLUE,
    IMMERSED,
    KACHCHH_FINER,
    PUBCHEM_INDIGO,
    SANGANER_INDIGO,
    SHIKARPUR,
    TWO_SHADES,
    Claim,
    sentence,
    stated,
    uid,
)

INDIGO_CID = 10215
INDIGO_COMPOUND = uid("compound/indigo")
AJRAKH = {"slug": "Kutch-Ajrakh", "name": "Kutch Ajrakh", "path": "/crafts/Kutch-Ajrakh"}
SHOPS = ("itokri.com", "jiomart.com", "houseofelegance.in", "gitagged.com", "instagram.com", "pinterest.com")
FERMENTED_SAID = (
    "Natural indigo is fermented with lime, dates and soda, while synthetic indigo often has 'Hydros'."
)
NAAND_SAID = "The cloth is dyed in indigo for 10 to 15 minutes, traditionally in a naand dug into the ground."


def block(block_id: str, kind: str, **fields: Any) -> dict[str, Any]:
    return {"id": block_id, "kind": kind, "version": 1, "reuse": None, **fields}


def prose(block_id: str, *said: tuple[str, tuple[Claim, ...]]) -> dict[str, Any]:
    sentences = [sentence(f"{block_id}.{n}", text, *claims) for n, (text, claims) in enumerate(said, 1)]
    return block(block_id, "prose", sentences=sentences)


def card(block_id: str, name: str, material: str, *facts: Claim) -> dict[str, Any]:
    return block(
        block_id,
        "material_card",
        materialId=uid(f"material/{material}"),
        compoundId=INDIGO_COMPOUND if "indigo" in material else None,
        termKey=None,
        name=name,
        materialKind="DYE",
        role="DYE",
        formula="C16H10N2O2" if "indigo" in material else None,
        pubchemCid=INDIGO_CID if "indigo" in material else None,
        wikidataId=None,
        localNames=[],
        facts=[stated(f"{block_id}.{n}", claim) for n, claim in enumerate(facts, 1)],
        handling=[],
    )


def molecule(block_id: str) -> dict[str, Any]:
    return block(
        block_id,
        "molecule_3d",
        compoundId=INDIGO_COMPOUND,
        pubchemCid=INDIGO_CID,
        name="Indigo",
        formula="C16H10N2O2",
        sourceId=PUBCHEM_INDIGO["id"],
    )


def craft(slug: str) -> dict[str, Any]:
    return {"slug": slug, "name": slug.replace("-", " "), "path": f"/crafts/{slug}"}


def node(key: str, label: str, block_id: str, *entries: tuple[str, Claim]) -> dict[str, Any]:
    crafts = [
        {
            "craft": craft(slug),
            "conceptIds": [uid(f"concept/{key}/{slug}")],
            "sentence": stated(f"{block_id}.{key}.{n}", claim),
        }
        for n, (slug, claim) in enumerate(entries, 1)
    ]
    return {"termKey": key, "label": label, "crafts": crafts}


def graph(block_id: str, *, alizarin: bool) -> dict[str, Any]:
    nodes = [
        node(
            "indigo",
            "Indigo",
            block_id,
            ("Kutch-Ajrakh", DHAMADKA_GROWN),
            ("Bagru-Hand-Block-Print", BAGRU_NIL),
            ("Dabu-Print", DABU_INDIGO),
            ("Sanganeri-Hand-Block-Printing", SANGANER_INDIGO),
        ),
        node(
            "alum", "Alum", block_id, ("Kutch-Ajrakh", ALUM_MORDANT), ("Bagru-Hand-Block-Print", BAGRU_ALUM)
        ),
    ]
    if alizarin:
        nodes.append(
            node(
                "alizarin",
                "Alizarin",
                block_id,
                ("Kutch-Ajrakh", ALIZARIN_1868),
                ("Bagh-Prints-Of-Madhya-Pradesh", BAGH_ALIZARIN),
            )
        )
    return block(block_id, "concept_graph", focus=AJRAKH, nodes=nodes)


def media(name: str, site: str, *, inline: bool, title: str | None = None) -> dict[str, Any]:
    return {
        "id": uid(f"media/{name}"),
        "display": "INLINE" if inline else "LINK_CARD",
        "provider": "openverse" if inline else "searxng",
        "pageUrl": f"https://{site}/{name}",
        "imageUrl": f"https://{site}/{name}.jpg",
        "width": None,
        "height": None,
        "title": title or f"Ajrakh {name.replace('-', ' ')}",
        "alt": f"Ajrakh {name.replace('-', ' ')}",
        "author": "nevil zaveri" if inline else None,
        "site": site,
        "credit": None,
        "licence": "CC BY 2.0" if inline else None,
        "licenceUrl": None,
        "sourceId": None,
        "retrievedAt": "2026-11-18T10:00:00Z",
    }


ZAVERI = media("dyed-cloth", "www.flickr.com/photos/nevilzaveri", inline=True)
VAT_PHOTO = media("indigo-vat", "commons.wikimedia.org/wiki", inline=True)
ITOKRI = media("kutch-ajrakh-dress", "www.itokri.com/products", inline=False, title="Buy Kutch Ajrakh Dress")
JIOMART = media("ajrakh-saree", "www.jiomart.com/p", inline=False)
INSTAGRAM = media("indigo-from-india", "www.instagram.com/p", inline=False)
GITAGGED = media("gi-ajrakh", "gitagged.com/ajrakh", inline=False)
ELEGANCE = media("indigo-duo", "houseofelegance.in/collections", inline=False)
PINTEREST = media("ajrakh-pin", "in.pinterest.com/pin", inline=True)


def pictures(block_id: str, *shown: tuple[dict[str, Any], tuple[Claim, ...]]) -> dict[str, Any]:
    items = [
        {"media": picture, "claimIds": [claim.id for claim in claims], "relevance": "TEXT"}
        for picture, claims in shown
    ]
    return block(block_id, "images", items=items)


def zoom(block_id: str) -> dict[str, Any]:
    compound = {
        "compoundId": INDIGO_COMPOUND,
        "pubchemCid": INDIGO_CID,
        "name": "Indigo",
        "formula": "C16H10N2O2",
        "sourceId": PUBCHEM_INDIGO["id"],
    }
    levels = [
        ("WORKSHOP", COTTON_COUNT, media("workshop", "commons.wikimedia.org/wiki", inline=True), None),
        ("CLOTH", KACHCHH_FINER, media("cloth", "commons.wikimedia.org/wiki", inline=True), None),
        ("MOLECULE", AJRAKH_INDIGO, None, compound),
    ]
    shaped = [
        {
            "level": level,
            "sentence": stated(f"{block_id}.{n}", claim),
            "district": None,
            "media": picture,
            "relevance": "TEXT" if picture else None,
            "compound": molecule_of,
        }
        for n, (level, claim, picture, molecule_of) in enumerate(levels, 1)
    ]
    return block(block_id, "zoom_story", levels=shaped, datasets=[], boundaryCaption=None)


def supply(block_id: str) -> dict[str, Any]:
    pairs = [
        ("Indigo", "Shikarpur", SHIKARPUR),
        ("Indigo", "Dhamadka", SHIKARPUR),
        ("Indigofera", "India", CONFINED),
    ]
    links = [
        {
            "material": material,
            "materialId": None,
            "termKey": None,
            "origin": origin,
            "wikidataId": None,
            "latitude": None,
            "longitude": None,
            "sentence": stated(f"{block_id}.{n}", claim),
        }
        for n, (material, origin, claim) in enumerate(pairs, 1)
    ]
    return block(block_id, "supply_map", links=links)


def seat(block_id: str, name: str, *said: tuple[str, Claim]) -> dict[str, Any]:
    take = [sentence(f"{block_id}.{n}", text, claim) for n, (text, claim) in enumerate(said, 1)]
    return block(block_id, "expert_view", seat=name, take=take, agreesWith=[], differs=[])


def ladder(block_id: str) -> dict[str, Any]:
    stages = [
        (8, "Indigo dyeing", "DYE", (TWO_SHADES, GREEN_BLUE)),
        (9, "Washing out the resist", "WASH", (IMMERSED,)),
    ]
    shaped = [
        {
            "stageId": uid(f"stage/{ordinal}"),
            "ordinal": ordinal,
            "name": name,
            "stageType": stage_type,
            "level": "PROVISIONAL",
            "sentences": [stated(f"{block_id}.{ordinal}.{n}", claim) for n, claim in enumerate(claims, 1)],
            "materials": [],
            "conditions": [],
            "reactionIds": [],
        }
        for ordinal, name, stage_type, claims in stages
    ]
    return block(block_id, "process_ladder", craft=AJRAKH, processId=uid("process/ajrakh"), stages=shaped)
