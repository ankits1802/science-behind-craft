"use client";

import { useCallback, useMemo, useState } from "react";

import { failureMessage, useRemote, type Remote } from "@/components/hooks/useRemote";
import { ChoroplethLegend, choroplethTone } from "@/components/map/ChoroplethLegend";
import { DistrictFills, DistrictTag, NO_DATA_TONE } from "@/components/map/DistrictLayer";
import { IndiaMapStage } from "@/components/map/IndiaMapStage";
import type { MapPoint } from "@/components/map/layout";
import { MapAttribution } from "@/components/map/MapAttribution";
import { loadShapes, type DistrictShape } from "@/components/map/shapeGeometry";
import { RetryLine } from "@/components/RemotePanels";
import { fetchMapLayer } from "@/lib/mapLayers";
import type { BoundaryNote, MapLayer } from "@/lib/regionContract";
import { districtReading, layerFills } from "@/lib/regionView";

type Pinned = { layerId: string; lgd: number };

export function MapLayerView({ points, layerId, boundary }: { points: MapPoint[]; layerId: string | null; boundary: BoundaryNote | null }) {
  const shapes = useRemote(layerId ? loadShapes : null);
  const loadLayer = useCallback(() => fetchMapLayer(layerId as string), [layerId]);
  const layer = useRemote(layerId ? loadLayer : null);
  const [hovered, setHovered] = useState<number | null>(null);
  const [pinned, setPinned] = useState<Pinned | null>(null);
  const data = layer.data;
  const fills = useMemo(() => (data ? layerFills(data) : null), [data]);
  const fillOf = useCallback(
    (shape: DistrictShape) => {
      if (!fills || !data) return null;
      const index = fills.get(shape.lgd);
      return index === undefined ? NO_DATA_TONE : choroplethTone(index, data.classes.length);
    },
    [data, fills]
  );
  const select = useCallback(
    (lgd: number) => setPinned((current) => (layerId && !(current?.layerId === layerId && current.lgd === lgd) ? { layerId, lgd } : null)),
    [layerId]
  );

  const activeLgd = hovered ?? (pinned && pinned.layerId === layerId ? pinned.lgd : null);
  const activeShape = shapes.data && activeLgd !== null ? shapes.data.find((shape) => shape.lgd === activeLgd) : undefined;
  const under = data && shapes.data ? <DistrictFills shapes={shapes.data} fillOf={fillOf} onHover={setHovered} onSelect={select} /> : null;
  const over = data && activeShape ? <DistrictTag shape={activeShape} text={districtReading(data, activeShape.lgd)} /> : null;

  return (
    <IndiaMapStage
      points={points}
      listLabel="Places"
      layers={{ under, over }}
      footer={
        <>
          {layerId ? <LayerStatus layer={layer} shapes={shapes} /> : null}
          <MapAttribution boundary={boundary} />
        </>
      }
    />
  );
}

export function LayerStatus({ layer, shapes }: { layer: Remote<MapLayer>; shapes: Remote<DistrictShape[]> }) {
  const failure = layer.failure ?? shapes.failure;
  if (failure) {
    const retry = layer.failure ? layer.retry : shapes.retry;
    return <RetryLine message={failureMessage(failure, "Couldn't load this layer.")} onRetry={retry} className="mt-4 border-t border-line-200 pt-4" />;
  }
  if (!layer.data || !shapes.data) {
    return (
      <p role="status" className="mt-4 border-t border-line-200 pt-4 text-sm text-ink-500">
        Loading layer…
      </p>
    );
  }
  return <ChoroplethLegend layer={layer.data} />;
}
