from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from .base import ContractModel
from .component_specs_science_explainers import MaterialCardsSpec, ModelExplainerSpec, ProcessReplaySpec
from .component_specs_science_figures import (
    DiagramSpec,
    EquationCardSpec,
    Molecule3dSpec,
    StructureDiagramSpec,
)

__all__ = ["SCIENCE_KINDS", "SPEC_MODELS_SCIENCE"]

SPEC_MODELS_SCIENCE: Mapping[str, type[ContractModel]] = MappingProxyType(
    {
        "diagram": DiagramSpec,
        "equation_card": EquationCardSpec,
        "material_cards": MaterialCardsSpec,
        "model_explainer": ModelExplainerSpec,
        "molecule_3d": Molecule3dSpec,
        "process_replay": ProcessReplaySpec,
        "structure_diagram": StructureDiagramSpec,
    }
)
SCIENCE_KINDS = tuple(SPEC_MODELS_SCIENCE)
