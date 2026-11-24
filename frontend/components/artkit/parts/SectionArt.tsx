import { ART_KIT } from "@/lib/artKit";
import type { SectionLayer, SectionPart } from "@/lib/componentSpecsKit";

import { url, type KitIds, type PartIds } from "../kitIds";
import { INK, MaterialPath, rectPath, WELL } from "../surfaces";

const LEFT = 10;
const WIDTH = 100;
const TOP = 10;
const HEIGHT = 100;

function Band({ layer, ids, y, height }: { layer: SectionLayer; ids: KitIds; y: number; height: number }) {
  const d = rectPath(LEFT, y, WIDTH, height);
  if (layer.material === ART_KIT.earth) {
    return (
      <g data-kit-layer="earth">
        <path d={d} fill={WELL} />
        <path d={d} fill={url(ids.strata)} />
      </g>
    );
  }
  return (
    <g data-kit-layer={layer.material}>
      <MaterialPath d={d} material={layer.material} ids={ids} edge="none" />
    </g>
  );
}

export function SectionArt({ part, ids }: { part: SectionPart; ids: PartIds }) {
  const height = HEIGHT / part.layers.length;
  const seams = part.layers.slice(1).map((_, at) => TOP + height * (at + 1));
  return (
    <g data-kit-part="section" data-kit-layers={part.layers.length}>
      {part.layers.map((layer, at) => (
        <Band key={`${layer.label}-${at}`} layer={layer} ids={ids} y={TOP + height * at} height={height} />
      ))}
      <path d={seams.map((y) => `M${LEFT} ${y.toFixed(2)} H${LEFT + WIDTH}`).join(" ")} stroke={INK} strokeWidth=".8" />
      <path d={rectPath(LEFT, TOP, WIDTH, HEIGHT)} fill="none" stroke={INK} strokeWidth="1.2" />
      <path d={`M${LEFT - 4} ${TOP} H${LEFT + WIDTH + 4}`} stroke={INK} strokeWidth="1.6" strokeLinecap="round" />
    </g>
  );
}
