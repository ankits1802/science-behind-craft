from __future__ import annotations

import re
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from io import BytesIO
from types import MappingProxyType
from xml.sax.saxutils import escape, quoteattr

from .docx_parts import (
    CONTENT_TYPES,
    DOCUMENT_CLOSE,
    DOCUMENT_OPEN,
    IMAGE_RELATION,
    LINK_RELATION,
    PACKAGE_RELATIONS,
    PICTURE_TEMPLATE,
    STYLES_RELATION,
    DocColours,
    core_properties,
    styles_xml,
)

__all__ = ["EMU_PER_MM", "DocRun", "DocxWriter"]

EMU_PER_MM = 36000
FIXED_TIME = (2026, 1, 1, 0, 0, 0)
INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
VERTICAL = MappingProxyType({"sub": "subscript", "sup": "superscript"})


@dataclass(frozen=True)
class DocRun:
    text: str
    style: str = ""
    lang: str | None = None


@dataclass
class DocxWriter:
    title: str
    language: str
    colours: DocColours
    right_to_left: bool = False
    body: list[str] = field(default_factory=list)
    relations: list[str] = field(default_factory=list)
    media: list[tuple[str, bytes]] = field(default_factory=list)

    def paragraph(self, runs: Sequence[DocRun], style: str = "Normal", *, link: str | None = None) -> None:
        shown = "".join(self._run(run) for run in runs if run.text)
        if not shown:
            return
        if link:
            shown = f'<w:hyperlink r:id="{self._relation(LINK_RELATION, link, external=True)}">{shown}</w:hyperlink>'
        self.body.append(f"<w:p>{self._paragraph_properties(style)}{shown}</w:p>")

    def picture(self, png: bytes, size: tuple[int, int], *, description: str, width_mm: float) -> None:
        number = len(self.media) + 1
        name = f"media/figure{number}.png"
        self.media.append((name, png))
        relation = self._relation(IMAGE_RELATION, name, external=False)
        pixels_wide, pixels_high = size
        cx = round(width_mm * EMU_PER_MM)
        cy = round(cx * pixels_high / max(pixels_wide, 1))
        drawing = PICTURE_TEMPLATE.format(
            cx=cx, cy=cy, number=number, relation=relation, description=quoteattr(_clean(description))
        )
        self.body.append(f"<w:p>{self._paragraph_properties('Figure')}<w:r>{drawing}</w:r></w:p>")

    def output(self) -> bytes:
        out = BytesIO()
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as package:
            self._write(package, "[Content_Types].xml", CONTENT_TYPES)
            self._write(package, "_rels/.rels", PACKAGE_RELATIONS)
            self._write(package, "docProps/core.xml", core_properties(_clean(self.title), self.language))
            self._write(package, "word/styles.xml", styles_xml(self.colours))
            self._write(package, "word/_rels/document.xml.rels", self._document_relations())
            self._write(package, "word/document.xml", DOCUMENT_OPEN + "".join(self.body) + DOCUMENT_CLOSE)
            for name, data in self.media:
                info = zipfile.ZipInfo(f"word/{name}", date_time=FIXED_TIME)
                package.writestr(info, data, compress_type=zipfile.ZIP_STORED)
        return out.getvalue()

    def _paragraph_properties(self, style: str) -> str:
        bidi = "<w:bidi/>" if self.right_to_left else ""
        return f'<w:pPr><w:pStyle w:val="{style}"/>{bidi}</w:pPr>'

    def _run(self, run: DocRun) -> str:
        props: list[str] = []
        if run.style == "b":
            props.append("<w:b/>")
        if run.style == "i":
            props.append("<w:i/>")
        if run.style in VERTICAL:
            props.append(f'<w:vertAlign w:val="{VERTICAL[run.style]}"/>')
        if self.right_to_left:
            props.append("<w:rtl/>")
        if run.lang:
            props.append(f'<w:lang w:val="{escape(run.lang)}" w:bidi="{escape(run.lang)}"/>')
        styled = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
        return f'<w:r>{styled}<w:t xml:space="preserve">{escape(_clean(run.text))}</w:t></w:r>'

    def _relation(self, kind: str, target: str, *, external: bool) -> str:
        relation = f"rId{len(self.relations) + 2}"
        mode = ' TargetMode="External"' if external else ""
        self.relations.append(
            f'<Relationship Id="{relation}" Type="{kind}" Target={quoteattr(_clean(target))}{mode}/>'
        )
        return relation

    def _document_relations(self) -> str:
        styles = f'<Relationship Id="rId1" Type="{STYLES_RELATION}" Target="styles.xml"/>'
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{styles}{''.join(self.relations)}</Relationships>"
        )

    @staticmethod
    def _write(package: zipfile.ZipFile, name: str, text: str) -> None:
        info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
        package.writestr(info, text.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)


def _clean(text: str) -> str:
    return INVALID_XML.sub("", text)
