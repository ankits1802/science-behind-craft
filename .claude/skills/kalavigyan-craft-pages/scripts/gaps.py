import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4] / "backend" / "app" / "data" / "curation"
BAR = {"pictures": 8, "placedShare": 1.0, "chaptersWithPictures": 4, "afterShare": 0.5, "whyShare": 0.66, "nativeNames": 1}


def dossiers(args):
    if args:
        return [Path(a) for a in args]
    files = sorted(ROOT.glob("*.json")) + sorted((ROOT / "categories").glob("*.json"))
    return [f for f in files if not f.name.endswith(".check.json") and f.name != "index.json"]


def share(part, whole):
    return part / whole if whole else 0.0


def report(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    category = path.parent.name == "categories"
    pictures = d.get("pictures") or []
    placed = [p for p in pictures if p.get("placement")]
    roles = [p["placement"].get("role") for p in placed]
    chapters = {p["placement"].get("chapter") for p in placed}
    stages = d.get("stages") or []
    materials = d.get("materials") or []
    sources = d.get("sources") or []
    gaps = []
    if len(pictures) < BAR["pictures"]:
        gaps.append(f"pictures {len(pictures)}/{BAR['pictures']}+")
    if share(len(placed), len(pictures)) < BAR["placedShare"]:
        gaps.append(f"unplaced pictures {len(pictures) - len(placed)}")
    if "MASTHEAD" not in roles:
        gaps.append("no MASTHEAD")
    if len(chapters) < BAR["chaptersWithPictures"]:
        gaps.append(f"chapters with pictures {len(chapters)}/{BAR['chaptersWithPictures']}+")
    if not category and stages:
        after = sum(1 for s in stages if s.get("after"))
        why = sum(1 for s in stages if s.get("whyClaimId"))
        if share(after, len(stages)) < BAR["afterShare"]:
            gaps.append(f"stage after {after}/{len(stages)}")
        if share(why, len(stages)) < BAR["whyShare"]:
            gaps.append(f"stage why {why}/{len(stages)}")
    if not category and len(d.get("nativeNames") or []) < BAR["nativeNames"]:
        gaps.append("no native name")
    if not category and d.get("scope", "CRAFT") == "CRAFT" and not (d.get("market") or {}).get("gi"):
        gaps.append("no GI record (only if GI-registered)")
    maybe_plants = [m for m in materials if m.get("kind") in {"DYE", "FIBRE", "WOOD", "RESIN", "MORDANT"}]
    unnamed = [m["id"] for m in maybe_plants if not m.get("botanicalName")]
    if unnamed:
        gaps.append(f"check for plants without botanicalName: {', '.join(unnamed)}")
    ab = sum(1 for s in sources if s.get("reliability") in {"A", "B"})
    return {
        "dossier": path.stem,
        "claims": len(d.get("claims") or []),
        "sourcesAB": f"{ab}/{len(sources)}",
        "pictures": len(pictures),
        "placed": len(placed),
        "stages": len(stages),
        "reactions": len(d.get("reactions") or []),
        "nativeNames": len(d.get("nativeNames") or []),
        "gaps": gaps,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = [report(p) for p in dossiers([a for a in sys.argv[1:] if not a.startswith("--")])]
    if "--json" in sys.argv:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    for r in rows:
        head = f"{r['dossier'][:34]:34} claims {r['claims']:3} AB {r['sourcesAB']:>6} pics {r['pictures']:2}/{r['placed']:2} stages {r['stages']:2} rx {r['reactions']} names {r['nativeNames']}"
        print(head)
        print("    " + ("; ".join(r["gaps"]) if r["gaps"] else "meets the bar"))


if __name__ == "__main__":
    main()
