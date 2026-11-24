import type { HeatPart } from "@/lib/componentSpecsKit";

import type { PartIds } from "../kitIds";
import { INK, INK_FAINT, INK_SOFT, LinePath, PAPER, WELL } from "../surfaces";

const FLAME = "M60 34 C68 46 78 52 76 68 C75 80 68 88 60 88 C52 88 45 80 44 68 C43 56 54 50 60 34 Z";
const SIDE_FLAMES = ["M42 56 C47 64 50 70 48 80 C46 86 40 88 36 84 C32 78 34 68 42 56 Z", "M78 56 C86 68 88 78 84 84 C80 88 74 86 72 80 C70 70 73 64 78 56 Z"];
const INNER = "M60 58 C64 64 67 70 65 76 C64 80 62 82 60 82 C58 82 56 80 55 76 C54 70 56 64 60 58 Z";
const LOGS = ["M26 92 L94 104 L92 112 L24 100 Z", "M26 104 L94 92 L96 100 L28 112 Z"];
const DOME = "M12 108 C12 62 34 34 60 34 C86 34 108 62 108 108 Z";
const MOUTH = "M42 108 C42 86 78 86 78 108 Z";
const DIYA = "M24 84 C30 102 90 102 96 84 C80 90 40 90 24 84 Z";

function Sun() {
  const rays = Array.from({ length: 12 }, (_, at) => {
    const angle = (Math.PI * at) / 6;
    const [cos, sin] = [Math.cos(angle), Math.sin(angle)];
    return `M${(60 + 30 * cos).toFixed(1)} ${(60 + 30 * sin).toFixed(1)} L${(60 + 42 * cos).toFixed(1)} ${(60 + 42 * sin).toFixed(1)}`;
  });
  return (
    <>
      <circle cx="60" cy="60" r="22" fill={PAPER} stroke={INK} strokeWidth="1.4" />
      <circle cx="60" cy="60" r="15" fill="none" stroke={INK_FAINT} strokeWidth=".9" strokeDasharray="2 3" />
      <path d={rays.join(" ")} stroke={INK} strokeWidth="1.6" strokeLinecap="round" />
    </>
  );
}

function Flames({ ids, scale = 1 }: { ids: PartIds; scale?: number }) {
  return (
    <g transform={scale === 1 ? undefined : `translate(${60 - 60 * scale} ${88 - 88 * scale}) scale(${scale})`}>
      {SIDE_FLAMES.map((d) => (
        <LinePath key={d} d={d} ids={ids} />
      ))}
      <LinePath d={FLAME} ids={ids} />
      <path d={INNER} fill="none" stroke={INK_SOFT} strokeWidth="1.1" />
    </g>
  );
}

function Fire({ ids }: { ids: PartIds }) {
  return (
    <>
      <Flames ids={ids} />
      {LOGS.map((d) => (
        <LinePath key={d} d={d} ids={ids} texture="grain" />
      ))}
    </>
  );
}

function Furnace({ ids }: { ids: PartIds }) {
  return (
    <>
      <LinePath d={DOME} ids={ids} texture="speckle" />
      <path d={MOUTH} fill={WELL} stroke={INK} strokeWidth="1.2" />
      <Flames ids={ids} scale={0.34} />
      <path d="M104 96 L118 82" stroke={INK} strokeWidth="3" strokeLinecap="round" />
      <path d="M40 30 q4 -6 0 -12 M60 26 q4 -6 0 -12 M80 30 q4 -6 0 -12" fill="none" stroke={INK_FAINT} strokeWidth="1.2" strokeLinecap="round" />
    </>
  );
}

function Lamp({ ids }: { ids: PartIds }) {
  return (
    <>
      <LinePath d={DIYA} ids={ids} texture="speckle" />
      <path d="M86 86 L100 80" stroke={INK} strokeWidth="2" strokeLinecap="round" />
      <g transform="translate(66 30) scale(.5)">
        <LinePath d={FLAME} ids={ids} />
        <path d={INNER} fill="none" stroke={INK_SOFT} strokeWidth="1.6" />
      </g>
    </>
  );
}

export function HeatArt({ part, ids }: { part: HeatPart; ids: PartIds }) {
  return (
    <g data-kit-part="heat" data-kit-source={part.source}>
      {part.source === "sun" ? <Sun /> : null}
      {part.source === "fire" ? <Fire ids={ids} /> : null}
      {part.source === "furnace" ? <Furnace ids={ids} /> : null}
      {part.source === "lamp" ? <Lamp ids={ids} /> : null}
    </g>
  );
}
