"use client";

import { useCallback, useMemo, useState, type ReactNode } from "react";

import { failureMessage, useRemote, type Remote } from "@/components/hooks/useRemote";
import { ChoroplethLegend, choroplethTone } from "@/components/map/ChoroplethLegend";
import { DistrictFills, DistrictOutlines, DistrictTag, NO_DATA_TONE } from "@/components/map/DistrictLayer";
import { IndiaMapStage } from "@/components/map/IndiaMapStage";
import type { MapPoint } from "@/components/map/layout";
import { MapAttribution } from "@/components/map/MapAttribution";
import { loadShapes, type DistrictShape } from "@/components/map/shapeGeometry";
import { RetryLine } from "@/components/RemotePanels";
import { fetchMapLayer } from "@/lib/mapLayers";
import type { BoundaryNote, MapLayer } from "@/lib/regionContract";
import { districtReading, layerFills } from "@/lib/regionView";

export const OPEN_DISTRICT_TONE = "fill-transparent hover:fill-purple-200/70 dark:hover:fill-purple-800/60";

export type DistrictPick = { lgd: number | null; name: string | null; onPick: (lgd: number | null) => void; panel: ReactNode };

function useLayerFill(data: MapLayer | null) {
  const fills = useMemo(() => (data ? layerFills(data) : null), [data]);
  return useCallback(
    (shape: DistrictShape) => {
      if (!fills || !data) return OPEN_DISTRICT_TONE;
      const index = fills.get(shape.lgd);
      return index === undefined ? NO_DATA_TONE : choroplethTone(index, data.classes.length);
    },
    [data, fills]
  );
}

function tagText(data: MapLayer | null, lgd: number, pick: DistrictPick): string | null {
  if (data) return districtReading(data, lgd);
  return lgd === pick.lgd ? pick.name : null;
}

export function MapLayerView({ points, layerId, boundary, district }: { points: MapPoint[]; layerId: string | null; boundary: BoundaryNote | null; district: DistrictPick }) {
  const shapes = useRemote(loadShapes);
  const loadLayer = useCallback(() => fetchMapLayer(layerId as string), [layerId]);
  const layer = useRemote(layerId ? loadLayer : null);
  const [hovered, setHovered] = useState<number | null>(null);
  const data = layerId ? layer.data : null;
  const fillOf = useLayerFill(data);
  const { lgd: picked, onPick } = district;
  const select = useCallback((lgd: number) => onPick(picked === lgd ? null : lgd), [picked, onPick]);

  const activeLgd = hovered ?? picked;
  const activeShape = shapes.data && activeLgd !== null ? shapes.data.find((shape) => shape.lgd === activeLgd) : undefined;
  const pickedShape = shapes.data && picked !== null ? shapes.data.find((shape) => shape.lgd === picked) : undefined;
  const drawn = shapes.data && (data || !layerId);
  const under = drawn ? <DistrictFills shapes={shapes.data ?? []} fillOf={fillOf} onHover={setHovered} onSelect={select} /> : null;
  const text = activeShape ? tagText(data, activeShape.lgd, district) : null;
  const over = (
    <>
      {pickedShape ? <DistrictOutlines shapes={[pickedShape]} className="stroke-ink-900 dark:stroke-white" /> : null}
      {activeShape && text ? <DistrictTag shape={activeShape} text={text} /> : null}
    </>
  );

  return (
    <IndiaMapStage
      points={points}
      listLabel="Places"
      layers={{ under, over }}
      footer={
        <>
          {layerId ? <LayerStatus layer={layer} shapes={shapes} /> : null}
          {district.panel}
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
