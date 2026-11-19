import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from app.core.errors import InvalidInput
from app.data.craft_master_loader import DATA_DIR, load_master
from app.research.monograph_page import render_page, served_kit
from app.services.chapter_preview import PREVIEW_SITE
from app.services.monograph_document import (
    authored_document,
    craft_page_url,
    document_json,
    kit_sources,
    monograph_content,
    monograph_shell,
    page_parts,
)

__all__ = [
    "PUBLIC_KIT_DIR",
    "SERVED_FOLDERS",
    "SERVED_KIT_PREAMBLES",
    "built_kit",
    "built_page",
    "document_text",
    "monograph_content",
    "served_page_path",
    "stale_pages",
    "write_pages",
]

PUBLIC_MONOGRAPHS_DIR = DATA_DIR.parents[2] / "frontend" / "public" / "monographs"
PUBLIC_KIT_DIR = PUBLIC_MONOGRAPHS_DIR / "kit"
SERVED_FOLDERS: Mapping[str, str] = MappingProxyType({"Kutch-Ajrakh": "kutch-ajrakh"})
PAGE_FILE = "index.html"
KIT_FOLDER = "kit"
SERVED_KIT_PREAMBLES: Mapping[str, str] = MappingProxyType(
    {
        "monograph.js": "/* eslint-disable react-hooks/rules-of-hooks -- "
        "the kit is the approved page's plain browser script, not React */\n"
    }
)


def built_page(slug: str) -> str:
    content = monograph_content(slug)
    return render_page(monograph_shell(slug), content, parts=page_parts(content))


def built_kit() -> dict[str, str]:
    return {
        name: SERVED_KIT_PREAMBLES.get(name, "") + served_kit(source, file_name=name)
        for name, source in kit_sources().items()
    }


def served_page_path(slug: str) -> Path:
    return PUBLIC_MONOGRAPHS_DIR / SERVED_FOLDERS[slug] / PAGE_FILE


def document_text(slug: str, *, site: str) -> str:
    titles = {craft.slug: craft.name for craft in load_master()}
    if slug not in titles:
        raise InvalidInput(f"No craft of the master list has the slug {slug}")
    content = monograph_content(slug)
    document = authored_document(content, title=titles[slug], page_url=craft_page_url(site, slug))
    return document_json(document)


def stale_pages() -> list[str]:
    pages = [slug for slug in SERVED_FOLDERS if _read(served_page_path(slug)) != built_page(slug)]
    kit = [
        f"{KIT_FOLDER}/{name}" for name, text in built_kit().items() if _read(PUBLIC_KIT_DIR / name) != text
    ]
    return pages + kit


def write_pages() -> list[str]:
    for slug in SERVED_FOLDERS:
        served_page_path(slug).write_bytes(built_page(slug).encode("utf-8"))
    PUBLIC_KIT_DIR.mkdir(exist_ok=True)
    kit = built_kit()
    for name, text in kit.items():
        (PUBLIC_KIT_DIR / name).write_bytes(text.encode("utf-8"))
    return list(SERVED_FOLDERS) + [f"{KIT_FOLDER}/{name}" for name in kit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build_monograph")
    parser.add_argument(
        "--check", action="store_true", help="report served pages and kit files that differ from their build"
    )
    parser.add_argument(
        "--document", metavar="SLUG", help="write this monograph's document instead of the pages"
    )
    parser.add_argument("--out", type=Path, help="where --document writes the document")
    parser.add_argument("--site", default=PREVIEW_SITE, help="the site the document's page address names")
    args = parser.parse_args(argv)
    if args.document:
        if args.out is None:
            parser.error("--document needs --out")
        args.out.write_bytes(document_text(args.document, site=args.site).encode("utf-8"))
        print(json.dumps({"ok": True, "document": args.document, "out": str(args.out)}))
        return 0
    if args.check:
        stale = stale_pages()
        print(json.dumps({"ok": not stale, "stale": stale}))
        return 1 if stale else 0
    print(json.dumps({"ok": True, "written": write_pages()}))
    return 0


def _read(path: Path) -> str | None:
    return path.read_bytes().decode("utf-8") if path.is_file() else None


if __name__ == "__main__":
    raise SystemExit(main())
