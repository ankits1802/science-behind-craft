"use client";

import { useCallback, useMemo, type ReactNode } from "react";

import { useRemote } from "@/components/hooks/useRemote";
import { DistrictFills, PLACE_TONE } from "@/components/map/DistrictLayer";
import { LayerStatus, useMapLayer, usePaletteFill } from "@/components/map/MapLayerView";
import { StillHome, StillRelief, StillRivers } from "@/components/map/MapStillLayers";
import { MineralSymbols } from "@/components/map/physical/MineralsLayer";
import { MineralKey, ReliefKey, RiversKey } from "@/components/map/physical/PhysicalSide";
import { ReliefOver, ReliefUnder } from "@/components/map/physical/ReliefLayer";
import { RiversOver, RiversUnder } from "@/components/map/physical/RiversLayer";
import { loadShapes, shapePath, type DistrictShape } from "@/components/map/shapeGeometry";
import type { LayerNames, MapStill } from "@/components/map/timelineMapStill";
import { Skeleton } from "@/components/ui/Skeleton";
import { loadPhysical, mineralKeyRows, mineralSites, type MineralSite, type MineralsFile, type ReliefFile, type RiversFile } from "@/lib/mapPhysical";

export const DRAWING_MINERALS = "Drawing the mineral deposits";

export type DrawnLayers = { underlay: ReactNode; overlay: (scale: number) => ReactNode; key: ReactNode };
export type Physical = { relief: ReliefFile | null; rivers: RiversFile | null; minerals: MineralsFile | null; sites: readonly MineralSite[] };

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

export function ReliefUnderOrStill({ file, still }: { file: ReliefFile | null; still: MapStill | null }) {
  if (file) return <ReliefUnder file={file} />;
  return still?.relief ? <StillRelief still={still} bands={still.relief} /> : null;
}

export function RiversUnderOrStill({ file, still }: { file: RiversFile | null; still: MapStill | null }) {
  if (file) return <RiversUnder file={file} />;
  return still?.rivers ? <StillRivers still={still} rivers={still.rivers} lakes={still.lakes} /> : null;
}

export function HomeOrStill({ shapes, home, still }: { shapes: readonly DistrictShape[] | null; home: readonly number[]; still: MapStill | null }) {
  if (!home.length) return null;
  if (shapes) return <HomeHatch shapes={shapes} home={home} />;
  return still?.home ? <StillHome d={still.home} /> : null;
}

function MineralsKey({ layers, still }: { layers: Physical; still: MapStill | null }) {
  if (layers.minerals) return <MineralKey rows={mineralKeyRows(layers.minerals, layers.sites)} />;
  return still?.minerals ? <MineralKey rows={still.minerals} /> : <Skeleton shape="legend" label={DRAWING_MINERALS} className="border-t border-rule pt-3" />;
}

export function PhysicalKey({ names, layers, still = null }: { names: LayerNames; layers: Physical; still?: MapStill | null }) {
  return (
    <>
      {names.physical.includes("relief") ? <ReliefKey /> : null}
      {names.physical.includes("rivers") ? <RiversKey /> : null}
      {names.physical.includes("minerals") ? <MineralsKey layers={layers} still={still} /> : null}
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

export function useTimelineMapLayers(names: LayerNames, still: MapStill | null = null): DrawnLayers {
  const relief = usePhysical("relief", names);
  const rivers = usePhysical("rivers", names);
  const minerals = usePhysical("minerals", names);
  const sites = useMemo(() => (minerals ? mineralSites(minerals) : []), [minerals]);
  const district = useMapLayer(names.district);
  const fillOf = usePaletteFill(district.layer.data);
  const homes = useRemote(names.home.length ? loadShapes : null).data;
  const layers: Physical = { relief, rivers, minerals, sites };
  const underlay = (
    <>
      <ReliefUnderOrStill file={relief} still={still} />
      {district.layer.data && district.shapes.data ? <DistrictFills shapes={district.shapes.data} fillOf={fillOf} /> : null}
      <RiversUnderOrStill file={rivers} still={still} />
      <HomeOrStill shapes={homes} home={names.home} still={still} />
    </>
  );
  const key = (
    <div className="mt-3 grid min-w-0 gap-3" data-testid="timeline-layer-key">
      <PhysicalKey names={names} layers={layers} still={still} />
      {names.district ? <LayerStatus layer={district.layer} shapes={district.shapes} held={still?.district ?? null} /> : null}
    </div>
  );
  return { underlay, overlay: (scale) => <PhysicalOver layers={layers} scale={scale} />, key };
}
