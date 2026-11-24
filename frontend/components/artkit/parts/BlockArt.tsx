import type { BlockPart } from "@/lib/componentSpecsKit";

import { url, type PartIds } from "../kitIds";
import { MotifPattern } from "../motifs";
import { INK, INK_SOFT, LinePath, PAPER, SHADE } from "../surfaces";

const TOP = "M22 30 L36 18 H104 L90 30 Z";
const FRONT = "M22 30 H90 V58 H22 Z";
const SIDE = "M90 30 L104 18 V46 L90 58 Z";
const HANDLE = "M54 22 C54 14 58 6 63 6 C68 6 72 14 72 22 Z";
const PRINT = "M14 72 H106 V108 H14 Z";

export function BlockArt({ part, ids }: { part: BlockPart; ids: PartIds }) {
  const motif = `${ids.part}-motif`;
  const colour = part.paste ?? "--ink-2";
  return (
    <g data-kit-part="block">
      <defs>
        <MotifPattern id={motif} motif={part.motif} material={colour} size={16} />
      </defs>
      <LinePath d={SIDE} ids={ids} texture="grain" fill={SHADE} />
      <LinePath d={FRONT} ids={ids} texture="grain" fill={SHADE} />
      <LinePath d={TOP} ids={ids} texture="grain" />
      <LinePath d={HANDLE} ids={ids} texture="grain" />
      <path d="M22 58 H90" stroke={INK} strokeWidth="2.2" strokeLinecap="round" />
      <path d={PRINT} fill={PAPER} />
      <path d={PRINT} fill={url(motif)} />
      <path d={PRINT} fill="none" stroke={INK_SOFT} strokeWidth="1" />
      <path d="M56 62 V68 M60 64 L56 68 L52 64" fill="none" stroke={INK_SOFT} strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </g>
  );
}
