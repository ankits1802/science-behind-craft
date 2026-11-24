import type { ToolName } from "@/lib/artKit";
import type { ToolPart } from "@/lib/componentSpecsKit";

import type { PartIds } from "../kitIds";
import { INK, INK_SOFT, LinePath, MaterialPath, PAPER, SHADE } from "../surfaces";

const FIST = "M-13 -8 C-13 -12 -9 -14 -5 -14 H7 C11 -14 14 -11 14 -7 V6 C14 10 11 12 7 12 H-6 C-10 12 -13 9 -13 5 Z";
const THUMB = "M-13 -2 C-19 -2 -21 5 -16 8 C-13 10 -9 9 -8 5";
const KNUCKLES = "M-4 -14 V-7 M2 -14 V-7 M8 -13 V-7";

type Drawn = { body: string[]; tip?: string; steel?: string; grip: number };

const AXIS_TOOLS: Readonly<Record<Exclude<ToolName, "block">, Drawn>> = {
  brush: { body: ["M-42 -3 H8 V3 H-42 Z", "M8 -4 H18 V4 H8 Z"], tip: "M18 -4.5 C30 -4.5 38 -1.5 44 0 C38 1.5 30 4.5 18 4.5 Z", grip: -14 },
  chisel: { body: ["M-36 -6 C-38 -6 -40 -4 -40 0 C-40 4 -38 6 -36 6 H4 V-6 Z"], steel: "M4 -3 H34 L44 0 L34 3 H4 Z", grip: -18 },
  mallet: { body: ["M-42 -3 H14 V3 H-42 Z", "M14 -15 C14 -17 15 -18 17 -18 H37 C39 -18 40 -17 40 -15 V15 C40 17 39 18 37 18 H17 C15 18 14 17 14 15 Z"], grip: -20 },
  knife: { body: ["M-34 -5 C-36 -5 -37 -3 -37 0 C-37 3 -36 5 -34 5 H4 V-5 Z"], steel: "M4 -4 H38 C42 -4 45 -1 45 1 L4 4 Z", grip: -16 },
  stick: { body: ["M-42 -4 C-44 -4 -45 -2 -45 0 C-45 2 -44 4 -42 4 H42 C44 4 45 2 45 0 C45 -2 44 -4 42 -4 Z"], grip: -22 }
};

function Fist({ ids, x, y }: { ids: PartIds; x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <LinePath d={FIST} ids={ids} />
      <path d={KNUCKLES} fill="none" stroke={INK_SOFT} strokeWidth="1" strokeLinecap="round" />
      <path d={THUMB} fill={PAPER} stroke={INK} strokeWidth="1.2" strokeLinejoin="round" />
    </g>
  );
}

function Loaded({ d, load, ids, texture }: { d: string; load?: string | null; ids: PartIds; texture?: "grain" }) {
  return load ? <MaterialPath d={d} material={load} ids={ids} /> : <LinePath d={d} ids={ids} texture={texture} />;
}

function AxisTool({ part, ids, drawn }: { part: ToolPart; ids: PartIds; drawn: Drawn }) {
  const bodyLoad = part.tool === "stick" ? part.load : null;
  return (
    <g transform="translate(60 62) rotate(-32)">
      {drawn.body.map((d) => (
        <Loaded key={d} d={d} load={bodyLoad} ids={ids} texture="grain" />
      ))}
      {drawn.steel ? <LinePath d={drawn.steel} ids={ids} fill={SHADE} /> : null}
      {drawn.tip ? <Loaded d={drawn.tip} load={part.load} ids={ids} /> : null}
      {part.held !== false ? <Fist ids={ids} x={drawn.grip} y={0} /> : null}
    </g>
  );
}

function BlockInHand({ part, ids }: { part: ToolPart; ids: PartIds }) {
  return (
    <g>
      <LinePath d="M22 74 H90 V100 H22 Z" ids={ids} texture="grain" fill={SHADE} />
      <LinePath d="M90 74 L104 62 V88 L90 100 Z" ids={ids} texture="grain" fill={SHADE} />
      <LinePath d="M22 74 L36 62 H104 L90 74 Z" ids={ids} texture="grain" />
      {part.load ? <MaterialPath d="M22 100 H90 V104 H22 Z" material={part.load} ids={ids} /> : <path d="M22 100 H90" stroke={INK} strokeWidth="2.2" />}
      <LinePath d="M54 66 C54 56 58 48 63 48 C68 48 72 56 72 66 Z" ids={ids} texture="grain" />
      {part.held !== false ? <Fist ids={ids} x={63} y={42} /> : null}
    </g>
  );
}

export function ToolArt({ part, ids }: { part: ToolPart; ids: PartIds }) {
  return (
    <g data-kit-part="tool" data-kit-tool={part.tool} data-kit-held={part.held === false ? "no" : "yes"}>
      {part.tool === "block" ? <BlockInHand part={part} ids={ids} /> : <AxisTool part={part} ids={ids} drawn={AXIS_TOOLS[part.tool]} />}
    </g>
  );
}
