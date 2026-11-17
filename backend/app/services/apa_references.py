from __future__ import annotations

from collections.abc import Sequence

from app.data.export_assets import apa_style_path
from app.research.citation_export import CslItem

__all__ = ["apa_references"]


def apa_references(items: Sequence[CslItem]) -> list[str]:
    if not items:
        return []
    from citeproc import Citation, CitationItem, CitationStylesBibliography, CitationStylesStyle, formatter
    from citeproc.source.json import CiteProcJSON

    style = CitationStylesStyle(str(apa_style_path()), validate=False)
    source = CiteProcJSON([item.model_dump(mode="json", by_alias=True) for item in items])
    bibliography = CitationStylesBibliography(style, source, formatter.plain)
    for item in items:
        bibliography.register(Citation([CitationItem(item.id)]))
    written = [str(reference) for reference in bibliography.bibliography()]
    if [item.key for item in bibliography.items] != [item.id for item in items]:
        raise ValueError("the APA style lost the order of the citations it was given")
    return written
