import type { PastePart } from "@/lib/componentSpecsKit";

import { paint, url, type KitIds, type Moving, type PartIds } from "../kitIds";
import { MotifPattern, starPoints } from "../motifs";
import { INK, MaterialPath, MovingLayer, PAPER, rectPath } from "../surfaces";

const SLAB = rectPath(10, 66, 100, 36);
const SPREAD = "M10 66 V50 C22 44 32 54 46 48 C60 42 72 52 86 46 C96 42 104 46 110 48 V66 Z";
const GROUND = rectPath(14, 14, 92, 92);
const OUTLINES = [
  [38, 38],
  [82, 38],
  [38, 82],
  [82, 82]
];

function Ground({ part, ids, d }: { part: PastePart; ids: KitIds; d: string }) {
  if (part.on) return <MaterialPath d={d} material={part.on} ids={ids} />;
  return <path d={d} fill={PAPER} stroke={INK} strokeWidth="1.2" />;
}

function Applied({ part, ids, material }: { part: PastePart; ids: PartIds; material: string }) {
  if (part.form === "spread") return <MaterialPath d={SPREAD} material={material} ids={ids} />;
  if (part.form === "printed") {
    const id = `${ids.part}-${material.slice(2)}`;
    return (
      <>
        <defs>
          <MotifPattern id={id} motif="dots" material={material} size={20} />
        </defs>
        <path d={GROUND} fill={url(id)} />
      </>
    );
  }
  return (
    <g fill="none" stroke={paint(material)} strokeWidth="5" strokeLinejoin="round">
      {OUTLINES.map(([cx, cy]) => (
        <polygon key={`${cx}-${cy}`} points={starPoints(cx, cy, 17, 7.5)} />
      ))}
    </g>
  );
}

export function PasteArt({ part, ids, moving }: { part: PastePart; ids: PartIds; moving?: Moving }) {
  const rest = part.dried ?? part.material;
  return (
    <g data-kit-part="paste" data-kit-form={part.form}>
      <Ground part={part} ids={ids} d={part.form === "spread" ? SLAB : GROUND} />
      <Applied part={part} ids={ids} material={rest} />
      {part.dried && moving ? (
        <MovingLayer moving={moving}>
          <Applied part={part} ids={ids} material={part.material} />
        </MovingLayer>
      ) : null}
    </g>
  );
}
