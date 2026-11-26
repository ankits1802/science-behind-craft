import type { KitPart } from "@/lib/componentSpecsKit";

import type { Moving, PartIds } from "./kitIds";
import { BathArt } from "./parts/BathArt";
import { BlockArt } from "./parts/BlockArt";
import { ClothArt } from "./parts/ClothArt";
import { HeatArt } from "./parts/HeatArt";
import { PasteArt } from "./parts/PasteArt";
import { PieceArt } from "./parts/PieceArt";
import { SectionArt } from "./parts/SectionArt";
import { SpeciesArt } from "./parts/SpeciesArt";
import { ToolArt } from "./parts/ToolArt";
import { WaterArt } from "./parts/WaterArt";

export type PartBox = { x: number; y: number; size: number };

export function KitPartArt({ part, ids, moving }: { part: KitPart; ids: PartIds; moving?: Moving }) {
  switch (part.part) {
    case "cloth":
      return <ClothArt part={part} ids={ids} moving={moving} />;
    case "block":
      return <BlockArt part={part} ids={ids} />;
    case "bath":
      return <BathArt part={part} ids={ids} moving={moving} />;
    case "paste":
      return <PasteArt part={part} ids={ids} moving={moving} />;
    case "heat":
      return <HeatArt part={part} ids={ids} />;
    case "water":
      return <WaterArt part={part} ids={ids} />;
    case "tool":
      return <ToolArt part={part} ids={ids} />;
    case "section":
      return <SectionArt part={part} ids={ids} />;
    case "piece":
      return <PieceArt part={part} ids={ids} />;
    case "species":
      return <SpeciesArt part={part} ids={ids} moving={moving} />;
  }
}

export function PlacedPart({ part, ids, box, moving }: { part: KitPart; ids: PartIds; box: PartBox; moving?: Moving }) {
  return (
    <svg x={box.x} y={box.y} width={box.size} height={box.size} viewBox="0 0 120 120" overflow="visible">
      <KitPartArt part={part} ids={ids} moving={moving} />
    </svg>
  );
}

export const PANEL_BOXES: Readonly<Record<number, PartBox[]>> = {
  1: [{ x: 50, y: 10, size: 140 }],
  2: [
    { x: 6, y: 22, size: 116 },
    { x: 118, y: 22, size: 116 }
  ],
  3: [
    { x: 2, y: 10, size: 140 },
    { x: 150, y: 4, size: 76 },
    { x: 150, y: 80, size: 76 }
  ]
};
