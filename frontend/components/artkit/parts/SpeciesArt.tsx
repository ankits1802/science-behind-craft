import { KIT_REACTION_CLASS } from "@/lib/artKitMotion";
import type { SpeciesPart } from "@/lib/componentSpecsKit";

import type { Moving, PartIds } from "../kitIds";
import { INK, INK_SOFT, MaterialPath, PAPER } from "../surfaces";

export const BEAD = "M14 60 A46 46 0 1 0 106 60 A46 46 0 1 0 14 60 Z";
const CRACK = "M60 14 L51 40 L66 58 L52 80 L60 106";
const ARRIVAL = "M60 1 V11 M54 5 L60 11 L66 5";

function Crack({ moving }: { moving?: Moving }) {
  const lines = (
    <>
      <path d={CRACK} fill="none" stroke={PAPER} strokeWidth="5" strokeLinejoin="round" />
      <path d={CRACK} fill="none" stroke={INK} strokeWidth="1.4" strokeLinejoin="round" strokeLinecap="round" />
    </>
  );
  if (!moving) return <g data-kit-break="">{lines}</g>;
  return (
    <g data-kit-break="" className={KIT_REACTION_CLASS.break} data-kit-move={moving.panel}>
      {lines}
    </g>
  );
}

function Bead({ part, ids }: { part: SpeciesPart; ids: PartIds }) {
  if (part.material) return <MaterialPath d={BEAD} material={part.material} ids={ids} texture="speckle" />;
  return <path d={BEAD} fill={PAPER} stroke={INK_SOFT} strokeWidth="1.4" strokeDasharray="6 4" />;
}

export function SpeciesArt({ part, ids, moving }: { part: SpeciesPart; ids: PartIds; moving?: Moving }) {
  return (
    <g data-kit-part="species" data-kit-role={part.role}>
      <Bead part={part} ids={ids} />
      {part.breaks ? <Crack moving={moving} /> : null}
      {part.role === "reagent" ? <path d={ARRIVAL} fill="none" stroke={INK_SOFT} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /> : null}
    </g>
  );
}
