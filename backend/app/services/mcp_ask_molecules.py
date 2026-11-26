from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping

from app.core.errors import ExternalFailure, InvalidInput, NotConfigured
from app.research.component_specs_science_geometry import MoleculeGeometry
from app.research.mcp_ask import AskedAnswer, AskedSection
from app.research.mcp_ask_figures import AskedMolecule
from app.science.molecule_conformer import conformer_geometry, undrawn_elements

from .compose_components import ConformerReader

__all__ = ["ConformerOpener", "drawn_molecules"]

logger = logging.getLogger(__name__)

ConformerOpener = Callable[[], Awaitable[ConformerReader]]


async def drawn_molecules(answer: AskedAnswer, opener: ConformerOpener) -> AskedAnswer:
    cids = list(dict.fromkeys(_cids(answer)))
    if not cids:
        return answer
    try:
        reader = await opener()
    except NotConfigured as missing:
        logger.warning("the answer's molecules are drawn without their 3D models: %s", missing.message)
        return answer
    geometries = {cid: await _geometry(reader, cid) for cid in cids}
    return answer.model_copy(
        update={"sections": [_drawn(section, geometries) for section in answer.sections]}
    )


def _cids(answer: AskedAnswer) -> list[int]:
    return [
        figure.pubchem_cid
        for section in answer.sections
        for figure in section.figures
        if isinstance(figure, AskedMolecule)
    ]


async def _geometry(reader: ConformerReader, cid: int) -> MoleculeGeometry | None:
    try:
        sdf = await reader.conformer(cid)
    except ExternalFailure as failure:
        logger.warning("the 3D conformer of CID %s could not be read for an answer: %s", cid, failure)
        return None
    if sdf is None:
        return None
    try:
        geometry = conformer_geometry(sdf)
    except InvalidInput as unread:
        logger.warning("the 3D conformer of CID %s could not be read for an answer: %s", cid, unread)
        return None
    return None if undrawn_elements(geometry) else geometry


def _drawn(section: AskedSection, geometries: Mapping[int, MoleculeGeometry | None]) -> AskedSection:
    figures = [
        figure.model_copy(update={"geometry": geometries.get(figure.pubchem_cid)})
        if isinstance(figure, AskedMolecule)
        else figure
        for figure in section.figures
    ]
    return section.model_copy(update={"figures": figures})
