import { citationShape, shownLevelShape, UUID } from "@/lib/answerShapes";
import { envelope, explainerSentenceShape, TERM_KEY, WIKIDATA_ID, type BlockEnvelope, type ExplainerSentence } from "@/lib/explainerBlockBase";
import { MATERIAL_KINDS, MATERIAL_ROLES, REACTION_KINDS, reactionSpeciesShape, type ReactionSpecies } from "@/lib/scienceContract";
import { boolean, integer, list, nullable, object, oneOf, text, type Shape } from "@/lib/shape";
import type { Citation, EvidenceLevel } from "@/lib/types";

export const MOLECULE_CONFORMER_PATH = (pubchemCid: number) => `/molecules/${pubchemCid}/conformer`;

export type ReactionStep = {
  reactionId: string;
  stageId: string | null;
  kind: (typeof REACTION_KINDS)[number];
  label: string;
  species: ReactionSpecies[];
  equation: string | null;
  balanced: boolean;
  level: EvidenceLevel;
  citations: Citation[];
};
export type ReactionPlayerBlock = BlockEnvelope<"reaction_player"> & { steps: ReactionStep[] };
export type MaterialCardBlock = BlockEnvelope<"material_card"> & {
  materialId: string | null;
  compoundId: string | null;
  termKey: string | null;
  name: string;
  materialKind: (typeof MATERIAL_KINDS)[number] | null;
  role: (typeof MATERIAL_ROLES)[number] | null;
  formula: string | null;
  pubchemCid: number | null;
  wikidataId: string | null;
  localNames: string[];
  facts: ExplainerSentence[];
  handling: ExplainerSentence[];
};
export type Molecule3dBlock = BlockEnvelope<"molecule_3d"> & {
  compoundId: string;
  pubchemCid: number;
  name: string;
  formula: string | null;
  sourceId: string;
};

export const reactionPlayerBlockShape: Shape<ReactionPlayerBlock> = object<ReactionPlayerBlock>({
  ...envelope("reaction_player"),
  steps: list(
    object<ReactionStep>({
      reactionId: UUID,
      stageId: nullable(UUID),
      kind: oneOf(REACTION_KINDS),
      label: text,
      species: list(reactionSpeciesShape, 2),
      equation: nullable(text),
      balanced: boolean,
      level: shownLevelShape,
      citations: list(citationShape, 1)
    }),
    1
  )
});

export const materialCardBlockShape: Shape<MaterialCardBlock> = object<MaterialCardBlock>({
  ...envelope("material_card"),
  materialId: nullable(UUID),
  compoundId: nullable(UUID),
  termKey: nullable(TERM_KEY),
  name: text,
  materialKind: nullable(oneOf(MATERIAL_KINDS)),
  role: nullable(oneOf(MATERIAL_ROLES)),
  formula: nullable(text),
  pubchemCid: nullable(integer),
  wikidataId: nullable(WIKIDATA_ID),
  localNames: list(text),
  facts: list(explainerSentenceShape, 1),
  handling: list(explainerSentenceShape)
});

export const molecule3dBlockShape: Shape<Molecule3dBlock> = object<Molecule3dBlock>({
  ...envelope("molecule_3d"),
  compoundId: UUID,
  pubchemCid: integer,
  name: text,
  formula: nullable(text),
  sourceId: text
});
