"use client";

import { useCallback, useMemo, useState } from "react";

import { useRemote } from "@/components/hooks/useRemote";
import { choroplethTone } from "@/components/map/ChoroplethLegend";
import { DistrictFills, DistrictOutlines, DistrictTag, NO_DATA_TONE } from "@/components/map/DistrictLayer";
import { IndiaMap } from "@/components/map/IndiaMap";
import { MapAttribution } from "@/components/map/MapAttribution";
import { LayerStatus } from "@/components/map/MapLayerView";
import { loadShapes, type DistrictShape } from "@/components/map/shapeGeometry";
import type { MapLayerBlock } from "@/lib/explainerPlace";
import { fetchMapLayer } from "@/lib/mapLayers";
import { boundaryNote, isGone } from "@/lib/placeView";
import type { MapLayer } from "@/lib/regionContract";
import { districtReading, layerFills } from "@/lib/regionView";

const NO_POINTS: never[] = [];

function Readings({ layer, highlighted }: { layer: MapLayer; highlighted: readonly number[] }) {
  return (
    <p className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-700" data-testid="map-layer-readings">
      <svg width={14} height={14} aria-hidden className="shrink-0">
        <rect x={1} y={1} width={12} height={12} rx={3} className="fill-none stroke-ink-900" strokeWidth={2} />
      </svg>
      <span className="font-semibold text-ink-900">Outlined</span>
      <span className="tabular-nums">{highlighted.map((lgd) => districtReading(layer, lgd)).join(" · ")}</span>
    </p>
  );
}

export function MapLayerBlockView({ block }: { block: MapLayerBlock }) {
  const shapes = useRemote(loadShapes);
  const load = useCallback(() => fetchMapLayer(block.layer), [block.layer]);
  const layer = useRemote(load);
  const [hovered, setHovered] = useState<number | null>(null);
  const data = layer.data;
  const fills = useMemo(() => (data ? layerFills(data) : null), [data]);
  const fillOf = useCallback(
    (shape: DistrictShape) => {
      if (!fills || !data) return null;
      const index = fills.get(shape.lgd);
      return index === undefined ? NO_DATA_TONE : choroplethTone(index, data.classes.length);
    },
    [fills, data]
  );
  const outlined = useMemo(() => (shapes.data ?? []).filter((shape) => block.highlighted.includes(shape.lgd)), [shapes.data, block.highlighted]);
  if (isGone(layer.failure)) return null;

  const hoveredShape = hovered === null ? undefined : shapes.data?.find((shape) => shape.lgd === hovered);
  const tagged = hoveredShape ? [hoveredShape] : outlined;
  const under = data && shapes.data ? <DistrictFills shapes={shapes.data} fillOf={fillOf} onHover={setHovered} /> : null;
  const over = data ? (
    <>
      <DistrictOutlines shapes={outlined} className="stroke-ink-900" />
      <g className="max-sm:hidden">
        {tagged.map((shape) => (
          <DistrictTag key={shape.lgd} shape={shape} text={districtReading(data, shape.lgd)} />
        ))}
      </g>
    </>
  ) : null;

  return (
    <figure className="min-w-0" data-testid="map-layer-block" data-layer={block.layer}>
      <IndiaMap points={NO_POINTS} underlay={under} overlay={over} />
      {data ? <Readings layer={data} highlighted={block.highlighted} /> : null}
      <LayerStatus layer={layer} shapes={shapes} />
      <MapAttribution boundary={boundaryNote(block.boundaryCaption, block.datasets)} />
    </figure>
  );
}
