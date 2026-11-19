import type { ComponentViews } from "@/lib/componentViewContract";

import { Diagram } from "./Diagram";
import { EquationCard } from "./EquationCard";
import { MaterialCards } from "./MaterialCards";
import { ModelExplainer } from "./ModelExplainer";
import { Molecule3d } from "./Molecule3d";
import { ProcessReplay } from "./ProcessReplay";
import { StructureDiagram } from "./StructureDiagram";

export const VIEWS: ComponentViews = {
  diagram: Diagram,
  equation_card: EquationCard,
  material_cards: MaterialCards,
  model_explainer: ModelExplainer,
  molecule_3d: Molecule3d,
  process_replay: ProcessReplay,
  structure_diagram: StructureDiagram
};
