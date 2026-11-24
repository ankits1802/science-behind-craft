import type { ClothPart } from "@/lib/componentSpecsKit";

import { paint, url, type Moving, type PartIds } from "../kitIds";
import { MotifPattern } from "../motifs";
import { INK, INK_SOFT, MaterialPath, MovingLayer, PAPER, rectPath, shaded } from "../surfaces";

const SWATCH = rectPath(16, 14, 88, 86);
const LENGTH = "M4 32 H116 V86 H4 Z";
const LENGTH_TURN = "M94 86 L116 64 V86 Z";
const FOLDS = "M12 36 H98 C110 36 110 56 98 56 H22 C10 56 10 76 22 76 H98 C110 76 110 96 98 96 H12";

function Fringe() {
  return (
    <g stroke={INK_SOFT} strokeWidth="1" strokeLinecap="round">
      {Array.from({ length: 22 }, (_, at) => (
        <path key={at} d={`M${18 + at * 4} 100 V106`} />
      ))}
    </g>
  );
}

function Folded({ part, ids }: { part: ClothPart; ids: PartIds }) {
  return (
    <g fill="none" strokeLinecap="butt" strokeLinejoin="round">
      <path d={FOLDS} stroke={INK} strokeWidth="15.4" />
      <path d={FOLDS} stroke={paint(part.material)} strokeWidth="13" />
      <path d={FOLDS} stroke={url(ids.weave)} strokeWidth="13" />
    </g>
  );
}

function Flat({ part, ids, d }: { part: ClothPart; ids: PartIds; d: string }) {
  const print = part.printed ? `${ids.part}-print` : undefined;
  return <MaterialPath d={d} material={part.material} ids={ids} print={print} />;
}

export function ClothArt({ part, ids, moving }: { part: ClothPart; ids: PartIds; moving?: Moving }) {
  const d = part.form === "length" ? LENGTH : SWATCH;
  return (
    <g data-kit-part="cloth" data-kit-form={part.form}>
      {part.printed ? (
        <defs>
          <MotifPattern id={`${ids.part}-print`} motif={part.printed.motif} material={part.printed.material} size={part.form === "length" ? 18 : 22} />
        </defs>
      ) : null}
      {moving && part.form !== "folded" ? <path d={d} fill={PAPER} stroke={INK} strokeWidth="1.2" /> : null}
      <MovingLayer moving={moving}>{part.form === "folded" ? <Folded part={part} ids={ids} /> : <Flat part={part} ids={ids} d={d} />}</MovingLayer>
      {part.form === "swatch" ? <Fringe /> : null}
      {part.form === "length" ? (
        <>
          <path d={LENGTH_TURN} fill={shaded(part.material, 78)} stroke={INK} strokeWidth="1.2" strokeLinejoin="round" />
          <path d="M4 38 H112" stroke={INK_SOFT} strokeWidth=".8" strokeDasharray="3 3" />
        </>
      ) : null}
    </g>
  );
}
