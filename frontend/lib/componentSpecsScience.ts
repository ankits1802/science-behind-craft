import { codedFigureShape } from "@/lib/componentSpecsScienceCoded";
import { materialCardsShape, modelExplainerShape, processReplayShape } from "@/lib/componentSpecsScienceExplainers";
import { diagramShape, equationCardShape, molecule3dShape, structureDiagramShape } from "@/lib/componentSpecsScienceFigures";
import { choiceToggleShape, experimentLabShape } from "@/lib/componentSpecsScienceLab";
import { dipPlayerShape, reactionPlayerShape, stagePlayerShape } from "@/lib/componentSpecsSciencePlayers";
import type { Shape } from "@/lib/shape";

export const SCIENCE_KINDS = [
  "choice_toggle",
  "coded_figure",
  "diagram",
  "dip_player",
  "equation_card",
  "experiment_lab",
  "material_cards",
  "model_explainer",
  "molecule_3d",
  "process_replay",
  "reaction_player",
  "stage_player",
  "structure_diagram"
] as const;

export type ScienceKind = (typeof SCIENCE_KINDS)[number];

export const SPEC_SHAPES_SCIENCE: Readonly<Record<ScienceKind, Shape<unknown>>> = {
  choice_toggle: choiceToggleShape,
  coded_figure: codedFigureShape,
  diagram: diagramShape,
  dip_player: dipPlayerShape,
  equation_card: equationCardShape,
  experiment_lab: experimentLabShape,
  material_cards: materialCardsShape,
  model_explainer: modelExplainerShape,
  molecule_3d: molecule3dShape,
  process_replay: processReplayShape,
  reaction_player: reactionPlayerShape,
  stage_player: stagePlayerShape,
  structure_diagram: structureDiagramShape
};
