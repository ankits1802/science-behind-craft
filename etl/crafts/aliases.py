from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from common import read_json, write_json

from app.data.craft_master_loader import (
    ALIASES_FILE,
    CODES_FILE,
    CRAFT_ALIASES_FILE,
    CRAFT_WIKIDATA_FILE,
    MASTER_FILE,
    VOCABULARY_FILE,
    MasterCraft,
    SharedCodes,
    codes_normalise,
    parse_codes,
    parse_master,
)
from app.data.craft_text import (
    INDIC_BLOCKS,
    SCRIPT_LANG,
    alias_norm,
    ascii_key,
    script_of,
    to_latin,
    to_latin_spoken,
)

from traditions import IMMERSIVE_ROOT, IMMERSIVE_TO_MASTER

ACTIVE = "ACTIVE"
PROPOSED = "PROPOSED"

MASTER = "MASTER"
CURATED = "CURATED"
CROSS_PORTAL_CODE = "CROSS_PORTAL_CODE"
IMMERSIVE = "IMMERSIVE"
WIKIDATA = "WIKIDATA"
TRANSLITERATION = "TRANSLITERATION"

TRUST = {MASTER: 0, CURATED: 1, CROSS_PORTAL_CODE: 2, IMMERSIVE: 3, WIKIDATA: 4, TRANSLITERATION: 5}

GENERIC_WORDS = frozenset(
    {
        "embroidery",
        "work",
        "works",
        "craft",
        "crafts",
        "art",
        "arts",
        "painting",
        "paintings",
        "pottery",
        "print",
        "prints",
        "printing",
        "hand",
        "block",
        "carving",
        "carvings",
        "weaving",
        "textile",
        "textiles",
        "metal",
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
        "shawl",
        "terracotta",
        "clay",
        "handicraft",
        "handicrafts",
        "textile art",
        "dyeing",
        "dye",
        "resist",
        "cloth",
        "fabric",
        "lamp",
        "mat",
        "mats",
        "basket",
        "baskets",
        "musical",
        "instrument",
        "instruments",
        "drum",
        "jewel",
        "beads",
        "bead",
        "other",
        "others",
        "style",
        "technique",
        "indigo",
        "alizarin",
        "flower",
        "flowers",
        "gum",
    }
)

SCHEMES: dict[str, str] = {
    "Deva": "devanagari",
    "Beng": "bengali",
    "Guru": "gurmukhi",
    "Gujr": "gujarati",
    "Orya": "oriya",
    "Taml": "tamil",
    "Telu": "telugu",
    "Knda": "kannada",
    "Mlym": "malayalam",
}
STATE_SCRIPTS: dict[str, tuple[str, ...]] = {
    "Andhra Pradesh": ("Telu",),
    "Telangana": ("Telu",),
    "Tamil Nadu": ("Taml",),
    "Puducherry": ("Taml",),
    "Karnataka": ("Knda",),
    "Kerala": ("Mlym",),
    "Gujarat": ("Gujr",),
    "Punjab": ("Guru",),
    "Odisha": ("Orya",),
    "West Bengal": ("Beng",),
    "Tripura": ("Beng",),
    "Assam": ("Beng",),
    "Maharashtra": ("Deva",),
    "Goa": ("Deva",),
}
INDIC_SCRIPTS = frozenset(SCHEMES)

STATE_SUFFIX = re.compile(r"\s+of\s+[A-Z][A-Za-z ]+$")


def sha1_of(path: Path) -> str | None:
    return hashlib.sha1(path.read_bytes()).hexdigest() if path.exists() else None


def is_generic(norm: str) -> bool:
    tokens = norm.split()
    return not tokens or all(t in GENERIC_WORDS for t in tokens)


def entry(
    alias: str,
    source: str,
    *,
    lang: str | None = None,
    status: str = ACTIVE,
    via: str | None = None,
) -> dict[str, Any] | None:
    alias = " ".join(str(alias or "").split())
    if not alias:
        return None
    script = script_of(alias)
    norm = alias_norm(alias)
    if not norm or (source != MASTER and is_generic(ascii_key(alias) if script != "Latn" else norm)):
        return None
    if script in ("Latn", "Zyyy") and len(norm.replace(" ", "")) < 3:
        return None
    latin = ascii_key(alias)
    return {
        "alias": alias,
        "norm": norm,
        "latin": latin,
        "script": script,
        "lang": lang or ("en" if script == "Latn" else SCRIPT_LANG.get(script)),
        "source": source,
        "status": status,
        "via": via,
    }


def name_variants(name: str) -> list[str]:
    out = [name]
    outer = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()
    out.append(outer)
    out.extend(part.strip(" \"'“”") for part in re.findall(r"\(([^)]*)\)", name))
    out.append(STATE_SUFFIX.sub("", outer))
    seen: set[str] = set()
    result: list[str] = []
    for value in out:
        key = ascii_key(value)
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def common_romanisations(latin: str) -> list[str]:
    variants = {latin}
    ch = re.sub(r"c(?!h)", "ch", latin)
    variants.add(ch)
    for base in list(variants):
        variants.add(re.sub(r"m(?=[^aeioubpm\s])", "n", base))
    return sorted(v for v in variants if v)


def latin_forms(alias: str) -> list[str]:
    forms: list[str] = []
    for base in (to_latin(alias), to_latin_spoken(alias)):
        forms.extend(common_romanisations(ascii_key(base)))
    seen: set[str] = set()
    return [f for f in forms if f and not (f in seen or seen.add(f))]


def cross_script(alias: str, target: str) -> str | None:
    from indic_transliteration import sanscript

    source = script_of(alias)
    if source not in SCHEMES or target not in SCHEMES or source == target:
        return None
    if "Deva" not in (source, target):
        return None
    try:
        out = sanscript.transliterate(alias, SCHEMES[source], SCHEMES[target])
    except KeyError, ValueError:
        return None
    return out if out and out != alias and pure_script(out, target) else None


def pure_script(text: str, script: str) -> bool:
    base = next(b for b, name in INDIC_BLOCKS.items() if name == script)
    for ch in text:
        if ch.isspace() or ch in "()-.,'\u200c\u200d":
            continue
        if not base <= ord(ch) < base + 0x80:
            return False
    return True


def latin_to_devanagari(name: str, vocabulary: frozenset[str]) -> str | None:
    from indic_transliteration import sanscript

    tokens = [t for t in ascii_key(name).split() if t in vocabulary and t not in GENERIC_WORDS]
    if not tokens:
        return None
    words = [sanscript.transliterate(t, sanscript.ITRANS, sanscript.DEVANAGARI).removesuffix("\u094d") for t in tokens]
    out = " ".join(words)
    return out if script_of(out) == "Deva" else None


def vocabulary_tokens(text: str) -> frozenset[str]:
    tokens: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tokens.update(t for t in ascii_key(line).split() if len(t) > 2)
    return frozenset(tokens)


def transliterations(
    aliases: list[dict[str, Any]], states: Iterable[str], name: str, vocabulary: frozenset[str]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    targets: set[str] = {"Deva"}
    for state in states:
        targets.update(STATE_SCRIPTS.get(state, ()))
    indic = [a for a in aliases if a["script"] in INDIC_SCRIPTS]
    for alias in indic:
        lang = alias.get("lang") or SCRIPT_LANG.get(alias["script"])
        for form in latin_forms(alias["alias"]):
            made = entry(form, TRANSLITERATION, lang=f"{lang}-Latn", via=f"{alias['script']}-to-Latn")
            if made:
                out.append(made)
        for target in sorted(targets):
            converted = cross_script(alias["alias"], target)
            if converted:
                made = entry(
                    converted,
                    TRANSLITERATION,
                    lang=SCRIPT_LANG[target],
                    status=PROPOSED,
                    via=f"{alias['script']}-to-{target}",
                )
                if made:
                    out.append(made)
    if not any(a["script"] == "Deva" for a in indic):
        deva = latin_to_devanagari(name, vocabulary)
        if deva:
            made = entry(deva, TRANSLITERATION, lang="hi", status=PROPOSED, via="Latn-to-Deva")
            if made:
                out.append(made)
    return out


def curated_by_slug(crafts: tuple[MasterCraft, ...], curated: dict[str, Any]) -> dict[str, list[str]]:
    by_serial = {c.source_serial: c.slug for c in crafts}
    decisions = {codes_normalise(row["oldName"]): row for row in curated.get("crafts", [])}
    out: dict[str, list[str]] = {}
    for row in curated.get("crafts", []):
        slug = by_serial.get(row.get("sourceSerial"))
        if slug:
            out.setdefault(slug, []).append(row["oldName"])
    for row in curated.get("freeText", []):
        target = decisions.get(codes_normalise(row.get("sameAs")))
        slug = by_serial.get(target.get("sourceSerial")) if target else None
        if slug:
            out.setdefault(slug, []).append(row["text"])
    return out


def map_codes(
    crafts: tuple[MasterCraft, ...], codes: SharedCodes, known: dict[str, list[str]]
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]], list[str]]:
    from rapidfuzz import fuzz, process

    index: dict[str, set[str]] = {}
    for craft in crafts:
        if craft.is_catch_all:
            continue
        for variant in name_variants(craft.name):
            index.setdefault(codes_normalise(variant), set()).add(craft.slug)
    for slug, names in known.items():
        for name in names:
            key = codes_normalise(name)
            if key and not is_generic(key):
                index.setdefault(key, set()).add(slug)
    choices = {c.slug: ascii_key(c.name) for c in crafts if not c.is_catch_all}
    mapped: dict[str, dict[str, Any]] = {}
    ambiguous: dict[str, list[str]] = {}
    unmapped: list[str] = []
    for code in codes.crafts:
        hits: set[str] = set()
        for spelling in (code.name, *code.spellings):
            hits |= index.get(codes_normalise(spelling), set())
        if len(hits) == 1:
            mapped[code.code] = {"slug": next(iter(hits)), "via": "exact", "status": ACTIVE}
            continue
        if len(hits) > 1:
            ambiguous[code.code] = sorted(hits)
            continue
        best: list[tuple[str, float, str]] = []
        for spelling in (code.name, *code.spellings):
            best.extend(process.extract(ascii_key(spelling), choices, scorer=fuzz.token_sort_ratio, limit=2))
        best.sort(key=lambda row: -row[1])
        if best and best[0][1] >= 90:
            rivals = [row for row in best if row[2] != best[0][2]]
            if not rivals or best[0][1] - rivals[0][1] >= 5:
                mapped[code.code] = {"slug": best[0][2], "via": f"fuzzy {best[0][1]:.0f}", "status": PROPOSED}
                continue
        unmapped.append(code.code)
    return mapped, ambiguous, unmapped


def wikidata_names(record: dict[str, Any]) -> list[tuple[str, str]]:
    match = record.get("match") if record.get("status") == "MATCHED" else None
    if not match:
        return []
    out: list[tuple[str, str]] = []
    for lang, label in (match.get("labels") or {}).items():
        out.append((label, lang))
    for lang, values in (match.get("aliases") or {}).items():
        out.extend((value, lang) for value in values)
    enwiki = (match.get("enwiki") or {}).get("title")
    if enwiki:
        out.append((re.sub(r"\s*\([^)]*\)\s*$", "", enwiki), "en"))
    for site, title in (match.get("sitelinks") or {}).items():
        out.append((re.sub(r"\s*\([^)]*\)\s*$", "", title), site.removesuffix("wiki").replace("_", "-")))
    return out


def immersive_alt_names(root: Path = IMMERSIVE_ROOT) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for slug, master in IMMERSIVE_TO_MASTER.items():
        path = root / "traditions" / slug / "tradition.json"
        if not path.exists():
            continue
        data = read_json(path)
        out[master] = [data.get("name", ""), *data.get("alt_names", [])]
    return out


def dedupe(entries: Iterable[dict[str, Any] | None]) -> list[dict[str, Any]]:
    by_norm: dict[str, dict[str, Any]] = {}
    for item in entries:
        if not item:
            continue
        current = by_norm.get(item["norm"])
        if current is None:
            by_norm[item["norm"]] = {**item, "sources": [item["source"]]}
            continue
        sources = sorted(set(current["sources"]) | {item["source"]}, key=lambda s: TRUST[s])
        better = TRUST[item["source"]] < TRUST[current["source"]]
        status = ACTIVE if ACTIVE in (current["status"], item["status"]) else current["status"]
        base = {**item} if better else current
        by_norm[item["norm"]] = {**base, "sources": sources, "status": status}
    return sorted(by_norm.values(), key=lambda a: (TRUST[a["source"]], a["script"] != "Latn", a["norm"]))


def merge(
    crafts: tuple[MasterCraft, ...],
    codes: SharedCodes,
    curated: dict[str, Any],
    wikidata: dict[str, Any] | None = None,
    immersive: dict[str, list[str]] | None = None,
    vocabulary: frozenset[str] | None = None,
) -> dict[str, Any]:
    curated_names = curated_by_slug(crafts, curated)
    wd_by_slug = {row["slug"]: row for row in (wikidata or {}).get("crafts", [])}
    known: dict[str, list[str]] = {}
    for craft in crafts:
        names = list(curated_names.get(craft.slug, []))
        names.extend((immersive or {}).get(craft.slug, []))
        names.extend(text for text, lang in wikidata_names(wd_by_slug.get(craft.slug, {})) if lang == "en")
        if names:
            known[craft.slug] = names
    mapped, ambiguous, unmapped = map_codes(crafts, codes, known)
    codes_by_slug: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for code, info in mapped.items():
        codes_by_slug.setdefault(info["slug"], []).append((code, info))
    vocab = vocabulary or frozenset()

    result: dict[str, Any] = {}
    owners: dict[str, set[str]] = {}
    summary: dict[str, int] = {}
    for craft in crafts:
        found: list[dict[str, Any] | None] = []
        for variant in name_variants(craft.name):
            derived = variant != craft.name
            if derived and (craft.is_catch_all or is_generic(alias_norm(variant))):
                continue
            found.append(entry(variant, MASTER, via="derived" if derived else None))
        found.append(entry(craft.slug.replace("-", " "), MASTER, via="slug"))
        for name in curated_names.get(craft.slug, []):
            found.append(entry(name, CURATED))
        for code, info in codes_by_slug.get(craft.slug, []):
            spec = codes.craft(code)
            for spelling in (spec.name, *spec.spellings) if spec else ():
                found.append(entry(spelling, CROSS_PORTAL_CODE, status=info["status"], via=f"{code} {info['via']}"))
        for name in (immersive or {}).get(craft.slug, []):
            found.append(entry(name, IMMERSIVE))
        for text, lang in wikidata_names(wd_by_slug.get(craft.slug, {})):
            found.append(entry(text, WIKIDATA, lang=lang, via=wd_by_slug[craft.slug]["match"]["qid"]))
        base = dedupe(found)
        found.extend(transliterations(base, (*craft.state_of_practice, *craft.state_of_origin), craft.name, vocab))
        aliases = dedupe(found)
        for alias in aliases:
            owners.setdefault(alias["norm"], set()).add(craft.slug)
            summary[alias["source"]] = summary.get(alias["source"], 0) + 1
        result[craft.slug] = {
            "name": craft.name,
            "craftCodes": sorted(code for code, _ in codes_by_slug.get(craft.slug, [])),
            "aliases": aliases,
        }
    collisions = [{"norm": norm, "slugs": sorted(slugs)} for norm, slugs in sorted(owners.items()) if len(slugs) > 1]
    return {
        "version": 1,
        "about": "Every known name of each master craft, deduplicated by 'norm'. Latin names are folded "
        "(accents removed, lower case, punctuation to single spaces); Indic names keep their script in "
        "'norm' and carry an ASCII 'latin' key. 'source' is the most trusted origin, 'sources' every origin. "
        "PROPOSED rows are machine guesses (fuzzy code mapping, script-to-script transliteration) that the "
        "matcher must not use for an exact hit. A 'norm' listed under 'collisions' names more than one craft "
        "and is never an exact match on its own.",
        "trustOrder": sorted(TRUST, key=lambda s: TRUST[s]),
        "summary": dict(sorted(summary.items())),
        "codes": {"mapped": dict(sorted(mapped.items())), "ambiguous": ambiguous, "unmapped": sorted(unmapped)},
        "collisions": collisions,
        "crafts": result,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge every craft alias source into craft_aliases.json.")
    parser.add_argument("--output", default=str(CRAFT_ALIASES_FILE))
    parser.add_argument("--immersive-root", default=str(IMMERSIVE_ROOT))
    args = parser.parse_args(argv)
    crafts = parse_master(read_json(MASTER_FILE))
    codes = parse_codes(read_json(CODES_FILE))
    curated = read_json(ALIASES_FILE)
    wikidata = read_json(CRAFT_WIKIDATA_FILE) if CRAFT_WIKIDATA_FILE.exists() else None
    immersive = immersive_alt_names(Path(args.immersive_root))
    if not immersive:
        previous = read_json(Path(args.output)) if Path(args.output).exists() else {}
        immersive = {
            slug: [a["alias"] for a in row["aliases"] if a["source"] == IMMERSIVE]
            for slug, row in previous.get("crafts", {}).items()
        }
    vocabulary = vocabulary_tokens(VOCABULARY_FILE.read_text(encoding="utf-8"))
    result = merge(crafts, codes, curated, wikidata, immersive, vocabulary)
    result["inputs"] = {
        path.name: sha1_of(path) for path in (MASTER_FILE, CODES_FILE, ALIASES_FILE, CRAFT_WIKIDATA_FILE)
    }
    write_json(Path(args.output), result)
    total = sum(len(row["aliases"]) for row in result["crafts"].values())
    print(
        f"wrote {args.output}: {total} aliases for {len(result['crafts'])} crafts, "
        f"{len(result['codes']['mapped'])} codes mapped, {len(result['codes']['unmapped'])} unmapped, "
        f"{len(result['collisions'])} collisions"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
