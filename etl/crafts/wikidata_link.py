from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from common import CACHE_DIR, DATA_DIR, PoliteClient, write_json

from app.data.craft_master_loader import MasterCraft, load_master, shared_codes
from app.data.craft_text import STOP_TOKENS, ascii_key, to_latin_spoken

SPARQL = "https://query.wikidata.org/sparql"
OUTPUT = DATA_DIR / "craft_wikidata.json"

INDIA = "Q668"
GI_INDIA = "Q98399252"

LANGS = (
    "en",
    "hi",
    "bn",
    "ta",
    "te",
    "mr",
    "gu",
    "kn",
    "ml",
    "or",
    "pa",
    "as",
    "ur",
    "sa",
    "ne",
    "sd",
    "kok",
    "mai",
    "mni",
    "ks",
    "doi",
    "sat",
    "bho",
    "brx",
)

MATCHED = "MATCHED"
LOW_CONFIDENCE = "LOW_CONFIDENCE"
NO_MATCH = "NO_MATCH"
CATCH_ALL = "CATCH_ALL"

ACCEPT = 0.80
FLAG = 0.60
MARGIN = 0.05

CLAIM_PROPS = ("P31", "P279", "P17", "P495", "P131", "P625", "P373", "P18", "P1389", "P935")

POSITIVE = (
    "craft",
    "handicraft",
    "handloom",
    "textile",
    "fabric",
    "cloth",
    "print",
    "embroider",
    "weav",
    "dye",
    "paint",
    "art form",
    "artform",
    "folk art",
    "visual art",
    "pottery",
    "ceramic",
    "earthenware",
    "terracotta",
    "sculpt",
    "carv",
    "statue",
    "idol",
    "toy",
    "doll",
    "puppet",
    "mask",
    "jewel",
    "ornament",
    "bangle",
    "metalwork",
    "metalware",
    "brass",
    "bronze",
    "bell metal",
    "copper",
    "silver",
    "gold",
    "iron",
    "casting",
    "inlay",
    "marquetry",
    "lacquer",
    "lac ",
    "wood",
    "bamboo",
    "cane",
    "basket",
    "mat",
    "grass",
    "fibre",
    "fiber",
    "leather",
    "footwear",
    "shoe",
    "sandal",
    "chappal",
    "glass",
    "bead",
    "musical instrument",
    "instrument",
    "drum",
    "string instrument",
    "wind instrument",
    "lute",
    "flute",
    "sari",
    "saree",
    "shawl",
    "carpet",
    "rug",
    "durrie",
    "dhurrie",
    "garment",
    "clothing",
    "scarf",
    "stole",
    "turban",
    "quilt",
    "applique",
    "patchwork",
    "technique",
    "tradition",
    "style",
    "product",
    "lamp",
    "utensil",
    "vessel",
    "pot",
    "plate",
    "lock",
    "knife",
    "paper",
    "papier",
    "stone",
    "marble",
    "shell",
    "horn",
    "bone",
    "ivory",
    "mirror",
    "filigree",
    "enamel",
    "decorative",
    "furniture",
    "geographical indication",
)
NEGATIVE = (
    "human",
    "person",
    "village",
    "town",
    "city",
    "census town",
    "municipality",
    "district",
    "tehsil",
    "taluka",
    "mandal",
    "block of",
    "human settlement",
    "neighbourhood",
    "neighborhood",
    "suburb",
    "river",
    "lake",
    "mountain",
    "hill",
    "island",
    "temple",
    "mosque",
    "church",
    "fort",
    "palace",
    "railway station",
    "airport",
    "school",
    "college",
    "university",
    "organization",
    "organisation",
    "company",
    "business",
    "film",
    "album",
    "song",
    "single",
    "band",
    "television",
    "episode",
    "book",
    "novel",
    "literary work",
    "newspaper",
    "magazine",
    "politician",
    "family name",
    "surname",
    "given name",
    "taxon",
    "species",
    "genus",
    "battle",
    "election",
    "constituency",
    "fictional",
    "deity",
    "festival",
    "dance",
    "language",
    "ethnic group",
    "caste",
    "tribe",
    "people",
    "wikimedia disambiguation",
    "disambiguation",
    "wikimedia list",
    "list article",
    "wikimedia category",
    "scholarly article",
    "administrative territorial entity",
    "state of india",
    "union territory",
)
INDIAN_STATES = (
    "andhra pradesh",
    "arunachal pradesh",
    "assam",
    "bihar",
    "chhattisgarh",
    "goa",
    "gujarat",
    "haryana",
    "himachal pradesh",
    "jharkhand",
    "karnataka",
    "kerala",
    "madhya pradesh",
    "maharashtra",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "odisha",
    "orissa",
    "punjab",
    "rajasthan",
    "sikkim",
    "tamil nadu",
    "telangana",
    "tripura",
    "uttar pradesh",
    "uttarakhand",
    "west bengal",
    "jammu and kashmir",
    "kashmir",
    "ladakh",
    "delhi",
    "puducherry",
    "pondicherry",
    "chandigarh",
    "lakshadweep",
    "andaman",
    "dadra and nagar haveli",
    "daman and diu",
)


FAMILY_HINTS: dict[str, tuple[str, ...]] = {
    "Textiles-Based-Craft-Category": (
        "textile",
        "fabric",
        "cloth",
        "embroider",
        "stitch",
        "needle",
        "weav",
        "loom",
        "print",
        "dye",
        "sari",
        "saree",
        "shawl",
        "carpet",
        "rug",
        "durrie",
        "dhurrie",
        "applique",
        "quilt",
        "garment",
        "silk",
        "cotton",
        "wool",
        "handkerchief",
        "tie",
        "batik",
        "kalamkari",
        "brocade",
        "zari",
        "textile art",
    ),
    "Wood-Craft-Category": ("wood", "timber", "carv", "lacquer", "furniture", "toy", "inlay", "marquetry", "turn"),
    "Metal-Craft-Category": (
        "metal",
        "brass",
        "bronze",
        "bell metal",
        "copper",
        "silver",
        "gold",
        "iron",
        "steel",
        "tin",
        "alloy",
        "casting",
        "dhokra",
        "dokra",
        "bidri",
        "lock",
        "lamp",
        "utensil",
        "ware",
        "enamel",
        "filigree",
        "jewel",
    ),
    "Stone-Craft-Category": ("stone", "marble", "carv", "sculpt", "inlay", "agate", "granite", "soapstone", "jali"),
    "Mud-Based-Craft-Category": ("pottery", "ceramic", "terracotta", "clay", "earthenware", "mud", "pot", "glaze"),
    "Natural-Fibre-Grass-Work": (
        "grass",
        "fibre",
        "fiber",
        "bamboo",
        "cane",
        "rattan",
        "reed",
        "leaf",
        "basket",
        "mat",
        "coir",
        "jute",
        "sisal",
        "wicker",
        "weav",
        "palm",
    ),
    "Leather-Craft-Category": ("leather", "hide", "footwear", "shoe", "sandal", "chappal", "jutti", "puppet", "saddle"),
    "Paper-Craft-Category": ("paper", "papier", "mache", "kite", "sanjhi", "stencil", "cut"),
    "Musical-Instrument": (
        "instrument",
        "drum",
        "flute",
        "lute",
        "string",
        "wind",
        "percussion",
        "horn",
        "trumpet",
        "harp",
        "veena",
        "membranophone",
        "aerophone",
        "chordophone",
        "idiophone",
        "music",
    ),
    "Folk-Painting": ("paint", "art", "mural", "scroll", "pictorial", "drawing", "miniature", "artwork", "style"),
    "Jewellery": ("jewel", "ornament", "bead", "necklace", "bangle", "earring", "ring", "pendant"),
    "Figurines-And-Toys": ("toy", "doll", "figur", "puppet", "idol", "statue", "craft"),
    "Glass-And-Beads-Crafts": ("glass", "bead", "bangle"),
    "Lac-And-Wax-Crafts": ("lac", "wax", "bangle", "lacquer"),
    "Bone-Horn-Shell-Crafts": ("bone", "horn", "shell", "conch", "ivory", "coconut"),
}


def family_hints(craft: MasterCraft) -> tuple[str, ...] | None:
    return FAMILY_HINTS.get(craft.sub_category_slug) or FAMILY_HINTS.get(craft.category_slug)


GENERIC = frozenset(
    {
        "embroidery",
        "embroidered",
        "work",
        "works",
        "craft",
        "crafts",
        "art",
        "arts",
        "painting",
        "paintings",
        "pottery",
        "potteries",
        "print",
        "prints",
        "printing",
        "printed",
        "hand",
        "handmade",
        "block",
        "carving",
        "carvings",
        "carved",
        "weaving",
        "woven",
        "weave",
        "textile",
        "textiles",
        "metal",
        "metalware",
        "ware",
        "wares",
        "product",
        "products",
        "of",
        "the",
        "and",
        "india",
        "indian",
        "traditional",
        "folk",
        "wood",
        "wooden",
        "stone",
        "toy",
        "toys",
        "doll",
        "dolls",
        "jewellery",
        "jewelry",
        "bamboo",
        "cane",
        "brass",
        "bronze",
        "copper",
        "silver",
        "gold",
        "iron",
        "leather",
        "glass",
        "paper",
        "applique",
        "saree",
        "sari",
        "sarees",
        "shawl",
        "shawls",
        "craftwork",
        "kala",
        "items",
        "articles",
        "making",
        "industry",
        "style",
        "design",
        "designs",
        "terracotta",
        "clay",
    }
)


def distinctive(tokens: Iterable[str]) -> set[str]:
    return {t for t in tokens if t not in GENERIC and len(t) > 2}


def shares_distinctive(craft_names: Iterable[str], candidate: Iterable[str]) -> bool | None:
    from rapidfuzz import fuzz

    wanted: set[str] = set()
    for name in craft_names:
        wanted |= distinctive(ascii_key(name).split())
    if not wanted:
        return None
    have: set[str] = set()
    for name in candidate:
        have |= set(ascii_key(name).split())
    return any(fuzz.ratio(w, h) >= 85 for w in wanted for h in have)


@dataclass
class Candidate:
    qid: str
    found_by: set[str] = field(default_factory=set)
    labels: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, list[str]] = field(default_factory=dict)
    descriptions: dict[str, str] = field(default_factory=dict)
    sitelinks: dict[str, str] = field(default_factory=dict)
    claims: dict[str, list[Any]] = field(default_factory=dict)
    enwiki: dict[str, Any] = field(default_factory=dict)


def clean_term(text: str) -> str:
    return " ".join(re.sub(r"[\\\"\n\r\t]", " ", text).split())


def chunks(items: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def query_variants(craft: MasterCraft, extra: Iterable[str] = ()) -> list[str]:
    name = craft.name
    out: list[str] = [name]
    inner = re.findall(r"\(([^)]*)\)", name)
    outer = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()
    out.append(outer)
    out.extend(part.strip(" \"'“”") for part in inner)
    stripped = re.sub(r"\s+of\s+(" + "|".join(re.escape(s) for s in INDIAN_STATES) + r")$", "", outer, flags=re.I)
    out.append(stripped)
    out.extend(extra)
    seen: set[str] = set()
    result: list[str] = []
    for value in out:
        key = ascii_key(value)
        if key and key not in seen and len(key) > 2:
            seen.add(key)
            result.append(value.strip())
    return result


def _tokens(text: str) -> list[str]:
    return [t for t in ascii_key(text).split() if t not in STOP_TOKENS] or ascii_key(text).split()


def name_similarity(craft_names: Iterable[str], candidate_names: Iterable[str]) -> float:
    from rapidfuzz import fuzz

    best = 0.0
    craft_list = [n for n in craft_names if ascii_key(n)]
    for cand in candidate_names:
        ct = _tokens(cand)
        if not ct:
            continue
        cand_key = " ".join(ct)
        for name in craft_list:
            nt = _tokens(name)
            if not nt:
                continue
            name_key = " ".join(nt)
            cand_cover = sum(max(fuzz.ratio(t, u) for u in nt) for t in ct) / len(ct)
            craft_cover = sum(max(fuzz.ratio(u, t) for t in ct) for u in nt) / len(nt)
            tok = 0.6 * cand_cover + 0.4 * craft_cover
            whole = max(fuzz.ratio(name_key, cand_key), fuzz.token_sort_ratio(name_key, cand_key))
            best = max(best, tok / 100, whole / 100)
    return round(min(best, 1.0), 4)


def strip_disambiguation(title: str) -> tuple[str, str | None]:
    match = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", title)
    return (match.group(1), match.group(2)) if match else (title, None)


def candidate_names(cand: Candidate) -> list[str]:
    names: list[str] = []
    if "en" in cand.labels:
        names.append(cand.labels["en"])
    names.extend(cand.aliases.get("en", []))
    if cand.sitelinks.get("enwiki"):
        names.append(strip_disambiguation(cand.sitelinks["enwiki"])[0])
    if not names:
        for lang, label in cand.labels.items():
            if lang != "en":
                names.append(to_latin_spoken(label))
    return names


def _text_blob(cand: Candidate, labels: dict[str, str]) -> tuple[str, str]:
    types = " ".join(labels.get(q, "") for q in cand.claims.get("P31", []) + cand.claims.get("P279", []))
    title = cand.sitelinks.get("enwiki", "")
    disamb = strip_disambiguation(title)[1] or ""
    extra = " ".join(
        [
            cand.descriptions.get("en", ""),
            cand.enwiki.get("description", ""),
            " ".join(cand.enwiki.get("categories", [])),
            disamb,
        ]
    )
    return f" {types.lower()} ", f" {extra.lower()} "


def _has(blob: str, words: Iterable[str]) -> list[str]:
    found: list[str] = []
    for word in words:
        tail = r"(?:e?s)?(?![a-z])" if len(word.strip()) <= 3 else ""
        if re.search(r"(?<![a-z])" + re.escape(word) + tail, blob):
            found.append(word)
    return found


STRONG_NEGATIVE_TYPES = (
    "fruit",
    "material",
    "organism",
    "common name",
    "taxon",
    "series",
    "stadium",
    "cricket",
    "sports venue",
    "food",
    "chemical",
    "mineral",
    "film",
    "human",
    "settlement",
    "disambiguation",
    "animal product",
    "gem",
    "clast",
    "sediment",
    "shell",
)
STRONG_NEGATIVE_EXTRA = (
    "natural materials",
    "granularity of materials",
    "edible fruits",
    "mollusc common names",
    "gemstones",
    "sports venues",
    "cricket grounds",
)


def is_gi(cand: Candidate) -> tuple[bool, list[str]]:
    cats = [c for c in cand.enwiki.get("categories", []) if "geographical indication" in c.lower()]
    return (GI_INDIA in cand.claims.get("P1389", []) or bool(cats)), cats


def score(craft: MasterCraft, names: list[str], cand: Candidate, labels: dict[str, str]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    sim = name_similarity(names, candidate_names(cand))
    reasons.append(f"name {sim:.2f}")
    types, extra = _text_blob(cand, labels)
    pos_types = _has(types, POSITIVE)
    neg_types = _has(types, NEGATIVE)
    pos_extra = _has(extra, POSITIVE)
    neg_extra = _has(extra, NEGATIVE) if not types.strip() else []
    hard_negative = bool(neg_types and not pos_types) or bool(neg_extra and not pos_extra and not pos_types)
    strong = _has(types, STRONG_NEGATIVE_TYPES) or (_has(extra, STRONG_NEGATIVE_EXTRA) if not types.strip() else [])
    if strong:
        hard_negative = True
        neg_types = [*neg_types, *strong]
        pos_types = []
        pos_extra = []
    if pos_types or (pos_extra and not neg_types):
        type_score = 1.0
        reasons.append("craft type")
    elif hard_negative:
        type_score = 0.0
        reasons.append("non-craft type: " + ", ".join(sorted(set(neg_types or neg_extra))[:3]))
    else:
        type_score = 0.4
        reasons.append("type unknown")
    countries = set(cand.claims.get("P17", []) + cand.claims.get("P495", []))
    india_text = bool(re.search(r"\bindia|indian\b", extra)) or bool(_has(extra, INDIAN_STATES))
    if INDIA in countries or india_text:
        india = 1.0
        reasons.append("India")
    elif countries:
        india = 0.0
        reasons.append("other country")
    else:
        india = 0.5
    states = [s.lower() for s in (*craft.state_of_practice, *craft.state_of_origin) if s != "All India"]
    located = " ".join(labels.get(q, "") for q in cand.claims.get("P131", [])).lower()
    blob = f"{extra} {located} {cand.sitelinks.get('enwiki', '').lower()}"
    if states and any(s in blob for s in states):
        state = 1.0
        reasons.append("state")
    else:
        state = 0.5
    gi, _ = is_gi(cand)
    bonus = 0.05 if gi and craft.gi_status == "GI" else 0.0
    if bonus:
        reasons.append("GI agrees")
    confidence = 0.55 * sim + 0.25 * type_score + 0.10 * india + 0.10 * state + bonus
    if hard_negative:
        confidence = min(confidence, 0.45)
    if sim < 0.6:
        confidence = min(confidence, 0.55)
    if sim < 0.75:
        confidence = min(confidence, ACCEPT - 0.01)
    if type_score < 1.0 or india == 0.0:
        confidence = min(confidence, ACCEPT - 0.01)
    hints = family_hints(craft)
    if hints and not _has(f"{types} {blob}", hints):
        confidence = min(confidence, ACCEPT - 0.01)
        reasons.append("outside the craft's family")
    cand_names = candidate_names(cand)
    if shares_distinctive(names[:1], cand_names) is False:
        own = set().union(*(distinctive(ascii_key(n).split()) for n in cand_names)) if cand_names else set()
        if own:
            confidence = min(confidence, ACCEPT - 0.01)
            reasons.append("no shared distinctive word")
        else:
            confidence = min(confidence, FLAG - 0.01)
            reasons.append("generic item")
    return round(min(confidence, 1.0), 4), reasons


def decide(ranked: list[tuple[float, Candidate, list[str]]]) -> str:
    if not ranked:
        return NO_MATCH
    top = ranked[0][0]
    second = ranked[1][0] if len(ranked) > 1 else 0.0
    if top >= ACCEPT and top - second >= MARGIN:
        return MATCHED
    if top >= FLAG:
        return LOW_CONFIDENCE
    return NO_MATCH


class Linker:
    def __init__(self, client: PoliteClient) -> None:
        self.client = client

    def sparql(self, query: str) -> list[dict[str, Any]]:
        payload = self.client.get_json(
            SPARQL,
            {"format": "json"},
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
        )
        return payload["results"]["bindings"]

    def gi_pool(self) -> dict[str, str]:
        rows = self.sparql(
            f"SELECT ?item ?label WHERE {{ ?item wdt:P1389 wd:{GI_INDIA} . "
            "?item rdfs:label ?label . FILTER(LANG(?label) = 'en') }"
        )
        return {r["item"]["value"].rsplit("/", 1)[1]: r["label"]["value"] for r in rows}

    @staticmethod
    def _literal(text: str) -> str:
        return '"' + clean_term(text) + '"'

    @staticmethod
    def _qid(binding: dict[str, Any]) -> str:
        return binding["value"].rsplit("/", 1)[1]

    def wikipedia_search(self, terms: list[str], batch: int = 25) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for group in chunks(sorted({clean_term(t) for t in terms}), batch):
            values = " ".join(self._literal(t) for t in group)
            rows = self.sparql(
                f"SELECT ?term ?item ?ord WHERE {{ VALUES ?term {{ {values} }} "
                'SERVICE wikibase:mwapi { bd:serviceParam wikibase:endpoint "en.wikipedia.org" ; '
                'wikibase:api "Generator" ; mwapi:generator "search" ; mwapi:gsrsearch ?term ; '
                'mwapi:gsrnamespace "0" ; mwapi:gsrlimit "5" ; wikibase:limit "once" . '
                "?item wikibase:apiOutputItem mwapi:item . ?ord wikibase:apiOrdinal true . } }"
            )
            for row in sorted(rows, key=lambda r: int(r.get("ord", {}).get("value", 0))):
                if "item" in row:
                    out.setdefault(row["term"]["value"], []).append(self._qid(row["item"]))
        return out

    def wikidata_search(self, terms: list[str], batch: int = 25) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for group in chunks(sorted({clean_term(t) for t in terms}), batch):
            values = " ".join(self._literal(t) for t in group)
            rows = self.sparql(
                f"SELECT ?term ?item WHERE {{ VALUES ?term {{ {values} }} "
                'SERVICE wikibase:mwapi { bd:serviceParam wikibase:endpoint "www.wikidata.org" ; '
                'wikibase:api "Search" ; mwapi:srsearch ?term ; mwapi:srlimit "5" ; wikibase:limit "once" . '
                "?item wikibase:apiOutputItem mwapi:title . } }"
            )
            for row in rows:
                if "item" in row and self._qid(row["item"]).startswith("Q"):
                    out.setdefault(row["term"]["value"], []).append(self._qid(row["item"]))
        return out

    def entities(self, qids: list[str]) -> dict[str, dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        langs = ", ".join(f"'{lang}'" for lang in LANGS)
        sites = " ".join(f"<https://{lang}.wikipedia.org/>" for lang in LANGS)

        def blank() -> dict[str, Any]:
            return {"labels": {}, "aliases": {}, "descriptions": {}, "sitelinks": {}}

        for batch in chunks(sorted(qids), 150):
            values = " ".join(f"wd:{q}" for q in batch)
            rows = self.sparql(
                f"SELECT ?item ?kind ?text WHERE {{ VALUES ?item {{ {values} }} "
                "{ ?item rdfs:label ?text . BIND('label' AS ?kind) } UNION "
                "{ ?item skos:altLabel ?text . BIND('alias' AS ?kind) } UNION "
                "{ ?item schema:description ?text . BIND('description' AS ?kind) } "
                f"FILTER(LANG(?text) IN ({langs})) }}"
            )
            for row in rows:
                entity = found.setdefault(self._qid(row["item"]), blank())
                lang = row["text"].get("xml:lang", "")
                kind = row["kind"]["value"]
                text = row["text"]["value"]
                if kind == "label":
                    entity["labels"][lang] = {"value": text}
                elif kind == "alias":
                    entity["aliases"].setdefault(lang, []).append({"value": text})
                else:
                    entity["descriptions"][lang] = {"value": text}
            rows = self.sparql(
                f"SELECT ?item ?site ?title WHERE {{ VALUES ?item {{ {values} }} VALUES ?site {{ {sites} }} "
                "?article schema:about ?item ; schema:isPartOf ?site ; schema:name ?title . }"
            )
            for row in rows:
                entity = found.setdefault(self._qid(row["item"]), blank())
                lang = row["site"]["value"].removeprefix("https://").split(".", 1)[0]
                entity["sitelinks"][f"{lang.replace('-', '_')}wiki"] = {"title": row["title"]["value"]}
            for qid in batch:
                found.setdefault(qid, blank())
        return found

    def claims(self, qids: list[str]) -> dict[str, dict[str, list[Any]]]:
        out: dict[str, dict[str, list[Any]]] = {}
        props = " ".join(f"wdt:{p}" for p in CLAIM_PROPS)
        for batch in chunks(sorted(qids), 120):
            values = " ".join(f"wd:{q}" for q in batch)
            rows = self.sparql(
                f"SELECT ?item ?prop ?value WHERE {{ VALUES ?item {{ {values} }} VALUES ?prop {{ {props} }} "
                "?item ?prop ?value . }"
            )
            for row in rows:
                qid = row["item"]["value"].rsplit("/", 1)[1]
                prop = row["prop"]["value"].rsplit("/", 1)[1]
                value = row["value"]["value"]
                if value.startswith("http://www.wikidata.org/entity/"):
                    value = value.rsplit("/", 1)[1]
                out.setdefault(qid, {}).setdefault(prop, []).append(value)
        return out

    def coordinates(self, qids: list[str]) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for batch in chunks(sorted(qids), 200):
            values = " ".join(f"wd:{q}" for q in batch)
            rows = self.sparql(f"SELECT ?item ?c WHERE {{ VALUES ?item {{ {values} }} ?item wdt:P625 ?c . }}")
            for row in rows:
                point = _parse_coord(row["c"]["value"])
                if point:
                    out.setdefault(self._qid(row["item"]), point)
        return out

    def labels(self, qids: list[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for batch in chunks(sorted(qids), 200):
            values = " ".join(f"wd:{q}" for q in batch)
            rows = self.sparql(
                f"SELECT ?item ?label WHERE {{ VALUES ?item {{ {values} }} ?item rdfs:label ?label . "
                "FILTER(LANG(?label) = 'en') }"
            )
            for row in rows:
                out[row["item"]["value"].rsplit("/", 1)[1]] = row["label"]["value"]
        return out

    def enwiki_pages(self, titles: list[str], batch: int = 40) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for group in chunks(sorted(set(titles)), batch):
            values = " ".join(self._literal(t) for t in group)
            rows = self.sparql(
                f"SELECT ?title ?category WHERE {{ VALUES ?title {{ {values} }} "
                'SERVICE wikibase:mwapi { bd:serviceParam wikibase:endpoint "en.wikipedia.org" ; '
                'wikibase:api "Categories" ; mwapi:titles ?title ; mwapi:clshow "!hidden" . '
                "?category wikibase:apiOutput mwapi:category . } }"
            )
            for title in group:
                out.setdefault(title, {"categories": [], "coordinates": [], "description": ""})
            for row in rows:
                if "category" in row:
                    entry = out.setdefault(
                        row["title"]["value"], {"categories": [], "coordinates": [], "description": ""}
                    )
                    entry["categories"].append(row["category"]["value"].removeprefix("Category:"))
        for entry in out.values():
            entry["categories"] = sorted(set(entry["categories"]))
        return out


def _parse_coord(value: str) -> dict[str, float] | None:
    match = re.match(r"Point\(([-0-9.eE]+) ([-0-9.eE]+)\)", value)
    if not match:
        return None
    return {"lat": round(float(match.group(2)), 6), "lon": round(float(match.group(1)), 6)}


def describe(
    cand: Candidate, labels: dict[str, str], places: dict[str, dict[str, float]] | None = None
) -> dict[str, Any]:
    gi, gi_cats = is_gi(cand)
    enwiki = cand.sitelinks.get("enwiki")
    coords = [c for c in (_parse_coord(v) for v in cand.claims.get("P625", [])) if c]
    for c in cand.enwiki.get("coordinates", []):
        point = {"lat": round(c["lat"], 6), "lon": round(c["lon"], 6)}
        if point not in coords:
            coords.append(point)
    commons = cand.claims.get("P373", [])
    images = cand.claims.get("P18", [])
    return {
        "qid": cand.qid,
        "url": f"https://www.wikidata.org/wiki/{cand.qid}",
        "label": cand.labels.get("en"),
        "description": cand.descriptions.get("en"),
        "enwiki": {"title": enwiki, "url": "https://en.wikipedia.org/wiki/" + enwiki.replace(" ", "_")}
        if enwiki
        else None,
        "sitelinks": {site: title for site, title in sorted(cand.sitelinks.items()) if site != "enwiki"},
        "labels": dict(sorted(cand.labels.items())),
        "aliases": {lang: values for lang, values in sorted(cand.aliases.items()) if values},
        "instanceOf": [{"qid": q, "label": labels.get(q)} for q in cand.claims.get("P31", [])],
        "subclassOf": [{"qid": q, "label": labels.get(q)} for q in cand.claims.get("P279", [])],
        "country": [
            {"qid": q, "label": labels.get(q)} for q in cand.claims.get("P17", []) + cand.claims.get("P495", [])
        ],
        "locatedIn": [
            {"qid": q, "label": labels.get(q), "coordinates": (places or {}).get(q)}
            for q in cand.claims.get("P131", [])
        ],
        "coordinates": coords,
        "commonsCategory": commons[0] if commons else None,
        "image": images[0].rsplit("/", 1)[-1] if images else None,
        "gi": {
            "tagged": gi,
            "wikidataCertification": GI_INDIA in cand.claims.get("P1389", []),
            "wikipediaCategories": gi_cats,
        },
        "wikipediaCategories": cand.enwiki.get("categories", []),
    }


def link(limit: int | None = None, use_cache: bool = True) -> dict[str, Any]:
    from rapidfuzz import fuzz, process

    crafts = list(load_master())
    if limit:
        crafts = crafts[:limit]
    codes = shared_codes()
    with PoliteClient(cache_dir=CACHE_DIR if use_cache else None) as client:
        linker = Linker(client)
        gi_pool = linker.gi_pool()
        gi_choices = {qid: ascii_key(label) for qid, label in gi_pool.items()}
        pool: dict[str, Candidate] = {}
        per_craft: dict[str, set[str]] = {}
        names_for: dict[str, list[str]] = {}
        for craft in crafts:
            if craft.is_catch_all:
                continue
            code = codes.spelling_index.get(ascii_key(craft.name))
            extra = list(codes.craft(code).spellings[:3]) if code and codes.craft(code) else []
            variants = query_variants(craft, extra)
            names_for[craft.slug] = variants
            qids: set[str] = set()
            for text in variants[:3]:
                for _, sim, qid in process.extract(ascii_key(text), gi_choices, scorer=fuzz.token_sort_ratio, limit=2):
                    if sim >= 80:
                        qids.add(qid)
                        pool.setdefault(qid, Candidate(qid)).found_by.add("gi-pool")
            per_craft[craft.slug] = qids
        wiki_terms = sorted({clean_term(t) for v in names_for.values() for t in v[:3]})
        wd_terms = sorted({clean_term(t) for v in names_for.values() for t in v[:2]})
        print(f"searching {len(wiki_terms)} Wikipedia and {len(wd_terms)} Wikidata terms", flush=True)
        wiki_hits = linker.wikipedia_search(wiki_terms)
        print(f"wikipedia search done, {client.requests} requests", flush=True)
        wd_hits = linker.wikidata_search(wd_terms)
        print(f"wikidata search done, {client.requests} requests", flush=True)
        for slug, variants in names_for.items():
            for text in variants[:3]:
                for qid in wiki_hits.get(clean_term(text), []):
                    per_craft[slug].add(qid)
                    pool.setdefault(qid, Candidate(qid)).found_by.add("enwiki-search")
            for text in variants[:2]:
                for qid in wd_hits.get(clean_term(text), []):
                    per_craft[slug].add(qid)
                    pool.setdefault(qid, Candidate(qid)).found_by.add("wikidata-search")
        entities = linker.entities(list(pool))
        print(f"entities done, {client.requests} requests", flush=True)
        for qid, entity in entities.items():
            cand = pool.setdefault(qid, Candidate(qid))
            cand.labels = {k: v["value"] for k, v in entity.get("labels", {}).items()}
            cand.aliases = {k: [a["value"] for a in v] for k, v in entity.get("aliases", {}).items()}
            cand.descriptions = {k: v["value"] for k, v in entity.get("descriptions", {}).items()}
            cand.sitelinks = {k: v["title"] for k, v in entity.get("sitelinks", {}).items()}
        claims = linker.claims(list(pool))
        for qid, props in claims.items():
            if qid in pool:
                pool[qid].claims = props
        referenced = {
            v for cand in pool.values() for p in ("P31", "P279", "P17", "P495", "P131") for v in cand.claims.get(p, [])
        }
        labels = linker.labels(sorted(referenced))
        places = linker.coordinates(sorted({v for cand in pool.values() for v in cand.claims.get("P131", [])}))
        titles = [c.sitelinks["enwiki"] for c in pool.values() if c.sitelinks.get("enwiki")]
        pages = linker.enwiki_pages(titles)
        for cand in pool.values():
            title = cand.sitelinks.get("enwiki")
            if title and title in pages:
                cand.enwiki = pages[title]
        requests = client.requests
        hits = client.cache_hits

    records: list[dict[str, Any]] = []
    for craft in crafts:
        base = {
            "slug": craft.slug,
            "name": craft.name,
            "sourceSerial": craft.source_serial,
            "subCategorySlug": craft.sub_category_slug,
            "masterGiStatus": craft.gi_status,
        }
        if craft.is_catch_all:
            records.append(
                {**base, "status": CATCH_ALL, "confidence": None, "match": None, "candidate": None, "candidates": []}
            )
            continue
        ranked = sorted(
            (
                (*score(craft, names_for[craft.slug], pool[q], labels), pool[q])
                for q in per_craft.get(craft.slug, set())
                if q in entities
            ),
            key=lambda row: (-row[0], row[2].qid),
        )
        ranked3 = [(conf, cand, reasons) for conf, reasons, cand in ranked]
        status = decide(ranked3)
        top = ranked3[0] if ranked3 else None
        records.append(
            {
                **base,
                "status": status,
                "confidence": top[0] if top else None,
                "reasons": top[2] if top else [],
                "match": describe(top[1], labels, places) if top and status == MATCHED else None,
                "candidate": describe(top[1], labels, places) if top and status == LOW_CONFIDENCE else None,
                "candidates": [
                    {
                        "qid": cand.qid,
                        "label": cand.labels.get("en"),
                        "description": cand.descriptions.get("en"),
                        "confidence": conf,
                        "foundBy": sorted(cand.found_by),
                    }
                    for conf, cand, _ in ranked3[:3]
                ],
            }
        )
    resolve_shared(records)
    summary: dict[str, int] = {}
    for row in records:
        summary[row["status"]] = summary.get(row["status"], 0) + 1
    gi_disagree = [
        row["slug"]
        for row in records
        if row["match"] and row["masterGiStatus"] == "GI" and not row["match"]["gi"]["tagged"]
    ]
    return {
        "version": 1,
        "generatedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "about": "Wikidata and English Wikipedia matches for the 455 master crafts. MATCHED rows are "
        "confident; LOW_CONFIDENCE rows keep their best guess under 'candidate' and are never used as a "
        "match; NO_MATCH rows list what was considered. Wikidata content is CC0; Wikipedia titles and "
        "categories are CC BY-SA 4.0.",
        "thresholds": {"accept": ACCEPT, "flag": FLAG, "margin": MARGIN},
        "languages": list(LANGS),
        "summary": dict(sorted(summary.items())),
        "requests": {"network": requests, "cache": hits},
        "masterGiNotTaggedOnWikidata": gi_disagree,
        "crafts": records,
    }


def resolve_shared(records: list[dict[str, Any]]) -> None:
    owners: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        if row["status"] == MATCHED:
            owners.setdefault(row["match"]["qid"], []).append(row)
    for rows in owners.values():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda r: -r["confidence"])
        clear = rows[0]["confidence"] - rows[1]["confidence"] >= MARGIN
        for row in rows[1:] if clear else rows:
            row["status"] = LOW_CONFIDENCE
            row["candidate"] = row["match"]
            row["match"] = None
            row["reasons"] = [*row.get("reasons", []), "item shared with another craft"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Link master crafts to Wikidata and Wikipedia.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args(argv)
    result = link(limit=args.limit, use_cache=not args.no_cache)
    from pathlib import Path

    write_json(Path(args.output), result)
    print(f"wrote {args.output}: {result['summary']}, requests {result['requests']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
