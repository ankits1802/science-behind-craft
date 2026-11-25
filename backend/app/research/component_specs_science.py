from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from .base import ContractModel
from .component_specs_science_coded import CodedFigureSpec
from .component_specs_science_explainers import MaterialCardsSpec, ModelExplainerSpec, ProcessReplaySpec
from .component_specs_science_figures import (
    DiagramSpec,
    EquationCardSpec,
    Molecule3dSpec,
    StructureDiagramSpec,
)
from .component_specs_science_lab import ChoiceToggleSpec, ExperimentLabSpec
from .component_specs_science_players import DipPlayerSpec, ReactionPlayerSpec, StagePlayerSpec

__all__ = ["SCIENCE_KINDS", "SPEC_MODELS_SCIENCE"]

SPEC_MODELS_SCIENCE: Mapping[str, type[ContractModel]] = MappingProxyType(
    {
        "choice_toggle": ChoiceToggleSpec,
        "coded_figure": CodedFigureSpec,
        "diagram": DiagramSpec,
        "dip_player": DipPlayerSpec,
        "equation_card": EquationCardSpec,
        "experiment_lab": ExperimentLabSpec,
        "material_cards": MaterialCardsSpec,
        "model_explainer": ModelExplainerSpec,
        "molecule_3d": Molecule3dSpec,
        "process_replay": ProcessReplaySpec,
        "reaction_player": ReactionPlayerSpec,
        "stage_player": StagePlayerSpec,
        "structure_diagram": StructureDiagramSpec,
    }
)
SCIENCE_KINDS = tuple(SPEC_MODELS_SCIENCE)
