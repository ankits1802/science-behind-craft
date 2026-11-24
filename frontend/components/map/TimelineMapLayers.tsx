"use client";

import { useCallback, useMemo, type ReactNode } from "react";

import { useRemote } from "@/components/hooks/useRemote";
import { DistrictFills, PLACE_TONE } from "@/components/map/DistrictLayer";
import { LayerStatus, useMapLayer, usePaletteFill } from "@/components/map/MapLayerView";
import { MineralSymbols } from "@/components/map/physical/MineralsLayer";
import { MineralKey, ReliefKey, RiversKey } from "@/components/map/physical/PhysicalSide";
import { ReliefOver, ReliefUnder } from "@/components/map/physical/ReliefLayer";
import { RiversOver, RiversUnder } from "@/components/map/physical/RiversLayer";
import { loadShapes, shapePath, type DistrictShape } from "@/components/map/shapeGeometry";
import { loadPhysical, mineralSites, type MineralSite, type MineralsFile, type ReliefFile, type RiversFile } from "@/lib/mapPhysical";

export type LayerNames = { physical: readonly string[]; district: string | null; home: readonly number[] };
export type DrawnLayers = { underlay: ReactNode; overlay: (scale: number) => ReactNode; key: ReactNode };
type Physical = { relief: ReliefFile | null; rivers: RiversFile | null; minerals: MineralsFile | null; sites: readonly MineralSite[] };

function usePhysical<K extends "relief" | "rivers" | "minerals">(id: K, names: LayerNames) {
  const load = useCallback(() => loadPhysical(id), [id]);
  return useRemote(names.physical.includes(id) ? load : null).data ?? null;
}

export function HomeHatch({ shapes, home }: { shapes: readonly DistrictShape[]; home: readonly number[] }) {
  const shown = shapes.filter((shape) => home.includes(shape.lgd));
  return (
    <g className="pointer-events-none" data-testid="timeline-home">
      {shown.map((shape) => (
        <path key={shape.lgd} d={shapePath(shape)} fillRule="evenodd" data-lgd={shape.lgd} className={PLACE_TONE} vectorEffect="non-scaling-stroke" />
      ))}
    </g>
  );
}

function PhysicalKey({ layers }: { layers: Physical }) {
  return (
    <>
      {layers.relief ? <ReliefKey file={layers.relief} /> : null}
      {layers.rivers ? <RiversKey /> : null}
      {layers.minerals ? <MineralKey file={layers.minerals} sites={layers.sites} /> : null}
    </>
  );
}

function PhysicalOver({ layers, scale }: { layers: Physical; scale: number }) {
  return (
    <>
      {layers.relief ? <ReliefOver file={layers.relief} scale={scale} /> : null}
      {layers.rivers ? <RiversOver file={layers.rivers} /> : null}
      {layers.minerals ? <MineralSymbols sites={layers.sites} scale={scale} /> : null}
    </>
  );
}

export function useTimelineMapLayers(names: LayerNames): DrawnLayers {
  const relief = usePhysical("relief", names);
  const rivers = usePhysical("rivers", names);
  const minerals = usePhysical("minerals", names);
  const sites = useMemo(() => (minerals ? mineralSites(minerals) : []), [minerals]);
  const district = useMapLayer(names.district);
  const fillOf = usePaletteFill(district.layer.data);
  const shapes = useRemote(names.home.length ? loadShapes : null).data;
  const layers: Physical = { relief, rivers, minerals, sites };
  const underlay = (
    <>
      {relief ? <ReliefUnder file={relief} /> : null}
      {district.layer.data && district.shapes.data ? <DistrictFills shapes={district.shapes.data} fillOf={fillOf} /> : null}
      {rivers ? <RiversUnder file={rivers} /> : null}
      {shapes ? <HomeHatch shapes={shapes} home={names.home} /> : null}
    </>
  );
  const key = (
    <div className="mt-3 grid min-w-0 gap-3" data-testid="timeline-layer-key">
      <PhysicalKey layers={layers} />
      {names.district ? <LayerStatus layer={district.layer} shapes={district.shapes} /> : null}
    </div>
  );
  return { underlay, overlay: (scale) => <PhysicalOver layers={layers} scale={scale} />, key };
}
