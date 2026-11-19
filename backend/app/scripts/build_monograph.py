import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from app.data.craft_master_loader import DATA_DIR
from app.research.monograph_page import MonographContent, render_page

MONOGRAPHS_DIR = DATA_DIR / "monographs"
PUBLIC_MONOGRAPHS_DIR = DATA_DIR.parents[2] / "frontend" / "public" / "monographs"
SERVED_FOLDERS: Mapping[str, str] = MappingProxyType({"Kutch-Ajrakh": "kutch-ajrakh"})
TEMPLATE_FILE = "template.html"
CONTENT_FILE = "content.json"
PAGE_FILE = "index.html"


def monograph_content(slug: str) -> MonographContent:
    raw = (MONOGRAPHS_DIR / slug / CONTENT_FILE).read_bytes().decode("utf-8")
    return MonographContent.model_validate_json(raw)


def built_page(slug: str) -> str:
    template = (MONOGRAPHS_DIR / slug / TEMPLATE_FILE).read_bytes().decode("utf-8")
    return render_page(template, monograph_content(slug))


def served_page_path(slug: str) -> Path:
    return PUBLIC_MONOGRAPHS_DIR / SERVED_FOLDERS[slug] / PAGE_FILE


def stale_pages() -> list[str]:
    return [
        slug
        for slug in SERVED_FOLDERS
        if served_page_path(slug).read_bytes().decode("utf-8") != built_page(slug)
    ]


def write_pages() -> list[str]:
    for slug in SERVED_FOLDERS:
        served_page_path(slug).write_bytes(built_page(slug).encode("utf-8"))
    return list(SERVED_FOLDERS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build_monograph")
    parser.add_argument(
        "--check", action="store_true", help="report served pages that differ from their build"
    )
    args = parser.parse_args(argv)
    if args.check:
        stale = stale_pages()
        print(json.dumps({"ok": not stale, "stale": stale}))
        return 1 if stale else 0
    print(json.dumps({"ok": True, "written": write_pages()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
