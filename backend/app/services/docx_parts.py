from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from xml.sax.saxutils import escape

__all__ = [
    "CONTENT_TYPES",
    "DOCUMENT_CLOSE",
    "DOCUMENT_OPEN",
    "IMAGE_RELATION",
    "LINK_RELATION",
    "PACKAGE_RELATIONS",
    "PICTURE_TEMPLATE",
    "STYLES_RELATION",
    "STYLE_NAMES",
    "DocColours",
    "core_properties",
    "styles_xml",
]

XML_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
RELATIONS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
IMAGE_RELATION = f"{RELATIONS}/image"
LINK_RELATION = f"{RELATIONS}/hyperlink"
STYLES_RELATION = f"{RELATIONS}/styles"
CONTENT_TYPES = (
    f"{XML_HEAD}"
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Default Extension="png" ContentType="image/png"/>'
    '<Default Extension="jpeg" ContentType="image/jpeg"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
    "</Types>"
)
PACKAGE_RELATIONS = (
    f"{XML_HEAD}"
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    f'<Relationship Id="rId1" Type="{RELATIONS}/officeDocument" Target="word/document.xml"/>'
    '<Relationship Id="rId2" '
    'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
    'Target="docProps/core.xml"/>'
    "</Relationships>"
)
DOCUMENT_OPEN = (
    f"{XML_HEAD}"
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    f'xmlns:r="{RELATIONS}" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>'
)
DOCUMENT_CLOSE = (
    '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/>'
    "</w:sectPr></w:body></w:document>"
)
PICTURE_TEMPLATE = (
    '<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
    '<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{number}" name="Figure {number}" descr={description}/>'
    '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
    '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
    '<pic:pic><pic:nvPicPr><pic:cNvPr id="{number}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
    '<pic:blipFill><a:blip r:embed="{relation}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
    '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
    '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
    "</a:graphicData></a:graphic></wp:inline></w:drawing>"
)


@dataclass(frozen=True)
class DocColours:
    heading: str
    body: str
    soft: str


@dataclass(frozen=True)
class _Style:
    name: str
    size: int
    colour: str
    bold: bool = False
    after: int = 120
    centred: bool = False


STYLE_NAMES: Mapping[str, str] = MappingProxyType(
    {
        "Title": "Title",
        "Meta": "Meta",
        "Heading1": "heading 1",
        "Heading2": "heading 2",
        "Heading3": "heading 3",
        "Term": "Term",
        "ListItem": "List item",
        "Quote": "Quote",
        "Kicker": "Kicker",
        "FigureTitle": "Figure title",
        "Figure": "Figure",
        "Caption": "Caption",
        "CaptionItem": "Caption item",
        "Note": "Note",
        "Credit": "Credit",
        "Reference": "Reference",
    }
)


def styles_xml(colours: DocColours) -> str:
    shown = "".join(_style(key, style) for key, style in _styles(colours).items())
    return (
        f"{XML_HEAD}"
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>'
        f'<w:sz w:val="21"/><w:szCs w:val="21"/><w:color w:val="{colours.body}"/></w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
        "</w:docDefaults>"
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
        f"{shown}"
        '<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/>'
        f'<w:rPr><w:color w:val="{colours.heading}"/><w:u w:val="single"/></w:rPr></w:style>'
        "</w:styles>"
    )


def core_properties(title: str, language: str) -> str:
    return (
        f"{XML_HEAD}"
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f"<dc:title>{escape(title)}</dc:title><dc:creator>KalaVigyan</dc:creator>"
        f"<dc:language>{escape(language)}</dc:language></cp:coreProperties>"
    )


def _styles(colours: DocColours) -> dict[str, _Style]:
    heading, body, soft = colours.heading, colours.body, colours.soft
    return {
        "Title": _Style(STYLE_NAMES["Title"], 48, body, bold=True, after=80),
        "Meta": _Style(STYLE_NAMES["Meta"], 19, soft, after=240),
        "Heading1": _Style(STYLE_NAMES["Heading1"], 34, heading, bold=True, after=160),
        "Heading2": _Style(STYLE_NAMES["Heading2"], 26, heading, bold=True),
        "Heading3": _Style(STYLE_NAMES["Heading3"], 22, body, bold=True, after=80),
        "Term": _Style(STYLE_NAMES["Term"], 21, body, bold=True, after=20),
        "ListItem": _Style(STYLE_NAMES["ListItem"], 21, body, after=80),
        "Quote": _Style(STYLE_NAMES["Quote"], 21, soft),
        "Kicker": _Style(STYLE_NAMES["Kicker"], 16, heading, bold=True, after=20),
        "FigureTitle": _Style(STYLE_NAMES["FigureTitle"], 22, body, bold=True, after=80),
        "Figure": _Style(STYLE_NAMES["Figure"], 18, body, after=80, centred=True),
        "Caption": _Style(STYLE_NAMES["Caption"], 18, body, after=40),
        "CaptionItem": _Style(STYLE_NAMES["CaptionItem"], 18, body, bold=True, after=20),
        "Note": _Style(STYLE_NAMES["Note"], 16, soft, after=40),
        "Credit": _Style(STYLE_NAMES["Credit"], 15, soft, after=20),
        "Reference": _Style(STYLE_NAMES["Reference"], 17, body, after=40),
    }


def _style(key: str, style: _Style) -> str:
    bold = "<w:b/>" if style.bold else ""
    centred = '<w:jc w:val="center"/>' if style.centred else ""
    return (
        f'<w:style w:type="paragraph" w:styleId="{key}"><w:name w:val="{style.name}"/>'
        '<w:basedOn w:val="Normal"/><w:qFormat/>'
        f'<w:pPr><w:spacing w:after="{style.after}"/>{centred}</w:pPr>'
        f'<w:rPr>{bold}<w:color w:val="{style.colour}"/><w:sz w:val="{style.size}"/><w:szCs w:val="{style.size}"/></w:rPr>'
        "</w:style>"
    )
