import type { Vessel } from "@/lib/artKit";
import type { BathPart } from "@/lib/componentSpecsKit";

import { paint, url, type KitIds, type Moving, type PartIds } from "../kitIds";
import { INK, INK_SOFT, LinePath, MaterialPath, MovingLayer, NEUTRAL_LIQUOR, WELL } from "../surfaces";

type Shape = { wall: string; liquor: string; surface: number; span: [number, number]; earth?: string; rim?: { cx: number; cy: number; rx: number; ry: number } };

const VESSELS: Readonly<Record<Vessel, Shape>> = {
  vat: {
    earth: "M0 40 H120 V120 H0 Z",
    wall: "M20 40 C20 92 36 114 60 114 C84 114 100 92 100 40 Z",
    liquor: "M25 54 C27 92 40 107 60 107 C80 107 93 92 95 54 Z",
    surface: 54,
    span: [26, 94],
    rim: { cx: 60, cy: 40, rx: 40, ry: 7 }
  },
  pot: {
    wall: "M34 34 C16 48 14 88 32 104 C44 114 76 114 88 104 C106 88 104 48 86 34 Z",
    liquor: "M21 58 H99 C101 82 96 96 85 103 C74 109 46 109 35 103 C24 96 19 82 21 58 Z",
    surface: 58,
    span: [21, 99],
    rim: { cx: 60, cy: 34, rx: 27, ry: 5 }
  },
  trough: { wall: "M8 44 H112 L104 106 H16 Z", liquor: "M12 58 H108 L102.3 100 H17.7 Z", surface: 58, span: [12, 108] },
  pit: { earth: "M0 40 H120 V120 H0 Z", wall: "M22 40 V110 H98 V40 Z", liquor: "M26 56 H94 V106 H26 Z", surface: 56, span: [26, 94] }
};

function Liquor({ shape, part, ids }: { shape: Shape; part: BathPart; ids: KitIds }) {
  if (part.liquor) return <MaterialPath d={shape.liquor} material={part.liquor} ids={ids} texture="ripple" edge={INK_SOFT} />;
  return (
    <>
      <path d={shape.liquor} fill={NEUTRAL_LIQUOR} />
      <path d={shape.liquor} fill={url(ids.ripple)} />
    </>
  );
}

function Piece({ part, ids, shape, moving }: { part: BathPart; ids: KitIds; shape: Shape; moving?: Moving }) {
  if (!part.piece) return null;
  const strip = `M52 22 H68 V${shape.surface + 34} H52 Z`;
  return (
    <>
      <MovingLayer moving={moving}>
        <MaterialPath d={strip} material={part.piece} ids={ids} />
      </MovingLayer>
      <path d={`M52 ${shape.surface} H68 V${shape.surface + 34} H52 Z`} fill={part.liquor ? paint(part.liquor) : NEUTRAL_LIQUOR} fillOpacity=".45" />
      <path d="M30 22 H90" stroke={INK} strokeWidth="2.4" strokeLinecap="round" />
    </>
  );
}

export function BathArt({ part, ids, moving }: { part: BathPart; ids: PartIds; moving?: Moving }) {
  const shape = VESSELS[part.vessel];
  return (
    <g data-kit-part="bath" data-kit-vessel={part.vessel}>
      {shape.earth ? (
        <>
          <path d={shape.earth} fill={WELL} />
          <path d={shape.earth} fill={url(ids.strata)} />
        </>
      ) : null}
      <LinePath d={shape.wall} ids={ids} />
      <Liquor shape={shape} part={part} ids={ids} />
      <path d={`M${shape.span[0]} ${shape.surface} H${shape.span[1]}`} stroke={INK_SOFT} strokeWidth="1" />
      {shape.rim ? <ellipse {...shape.rim} fill="none" stroke={INK} strokeWidth="1.4" /> : null}
      {shape.earth ? <path d="M0 40 H120" stroke={INK} strokeWidth="1.6" /> : null}
      <Piece part={part} ids={ids} shape={shape} moving={moving} />
    </g>
  );
}
