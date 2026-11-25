import type { ReactNode } from "react";

import { KIT_REACTION_CLASS } from "@/lib/artKitMotion";
import type { SpeciesPart } from "@/lib/componentSpecsKit";

import { partIds, type KitIds, type Moving } from "./kitIds";
import { PlacedPart, type PartBox } from "./KitPartArt";
import { INK } from "./surfaces";

const REACTION_ARROW = "M110 80 H129 M123 74 L130 80 L123 86";
const FRAME_TOP = 4;
const FRAME_HEIGHT = 152;
const COLUMN_WIDTH = 104;
const COLUMNS = [0, 136] as const;
const GAP = 8;
const ONE_ACROSS_MOST = 2;
const BEAD_MOST = 96;
const PAIRED_MOST = 48;

const rounded = (value: number) => Math.round(value * 100) / 100;

function column(left: number, count: number): PartBox[] {
  if (count === 0) return [];
  const across = count <= ONE_ACROSS_MOST ? 1 : 2;
  const rows = Math.ceil(count / across);
  const size = Math.min(across === 1 ? BEAD_MOST : PAIRED_MOST, (FRAME_HEIGHT - GAP * (rows - 1)) / rows);
  const x0 = left + (COLUMN_WIDTH - (across * size + GAP * (across - 1))) / 2;
  const y0 = FRAME_TOP + (FRAME_HEIGHT - (rows * size + GAP * (rows - 1))) / 2;
  return Array.from({ length: count }, (_, at) => ({ x: rounded(x0 + (at % across) * (size + GAP)), y: rounded(y0 + Math.floor(at / across) * (size + GAP)), size: rounded(size) }));
}

export function speciesBoxes(parts: readonly SpeciesPart[]): PartBox[] {
  const reactants = parts.flatMap((part, at) => (part.role === "product" ? [] : [at]));
  const products = parts.flatMap((part, at) => (part.role === "product" ? [at] : []));
  const boxes = new Map<number, PartBox>();
  [reactants, products].forEach((side, at) => column(COLUMNS[at], side.length).forEach((box, index) => boxes.set(side[index], box)));
  return parts.map((_, at) => boxes.get(at) as PartBox);
}

function Moves({ className, panel, children }: { className: string; panel: number | null; children: ReactNode }) {
  if (panel === null) return <g>{children}</g>;
  return (
    <g className={className} data-kit-move={panel}>
      {children}
    </g>
  );
}

type SceneProps = { parts: readonly SpeciesPart[]; ids: KitIds; name: string; panel: number | null };

export function SpeciesSceneArt({ parts, ids, name, panel }: SceneProps) {
  const boxes = speciesBoxes(parts);
  const moving: Moving | undefined = panel === null ? undefined : { className: KIT_REACTION_CLASS.break, panel };
  return (
    <g data-kit-reaction="">
      {parts.map((part, at) => (
        <Moves key={`${part.label}-${at}`} className={KIT_REACTION_CLASS[part.role]} panel={panel}>
          <PlacedPart part={part} ids={partIds(ids, `${name}-${at}`)} box={boxes[at]} moving={moving} />
        </Moves>
      ))}
      <Moves className={KIT_REACTION_CLASS.arrow} panel={panel}>
        <path d={REACTION_ARROW} fill="none" stroke={INK} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </Moves>
    </g>
  );
}
