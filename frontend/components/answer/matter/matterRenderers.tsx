import type { ComponentType } from "react";

import { MaterialCardView } from "@/components/answer/matter/MaterialCardView";
import { MoleculeView } from "@/components/answer/matter/MoleculeView";
import { ReactionPlayer } from "@/components/answer/matter/ReactionPlayer";
import type { MaterialCardBlock, Molecule3dBlock, ReactionPlayerBlock } from "@/lib/explainerMatter";

export const MATTER_RENDERERS: {
  reaction_player: ComponentType<{ block: ReactionPlayerBlock }>;
  material_card: ComponentType<{ block: MaterialCardBlock }>;
  molecule_3d: ComponentType<{ block: Molecule3dBlock }>;
} = {
  reaction_player: ReactionPlayer,
  material_card: MaterialCardView,
  molecule_3d: MoleculeView
};
