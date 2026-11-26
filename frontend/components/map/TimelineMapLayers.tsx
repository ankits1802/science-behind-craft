"use client";

import { useCallback, useMemo, type ReactNode } from "react";

import { useRemote } from "@/components/hooks/useRemote";
import { DistrictFills, PLACE_TONE } from "@/components/map/DistrictLayer";
import { LayerStatus, useMapLayer, usePaletteFill } from "@/components/map/MapLayerView";
import { PLAIN, StillHome, StillRelief, StillRivers, type Strength } from "@/components/map/MapStillLayers";
import { MineralSymbols } from "@/components/map/physical/MineralsLayer";
import { MineralKey, ReliefKey, RiversKey } from "@/components/map/physical/PhysicalSide";
import { ReliefOver, ReliefUnder } from "@/components/map/physical/ReliefLayer";
import { RiversOver, RiversUnder } from "@/components/map/physical/RiversLayer";
import { loadShapes, shapePath, type DistrictShape } from "@/components/map/shapeGeometry";
import type { LayerEmphasis, LayerNames, MapStill } from "@/components/map/timelineMapStill";
import { Skeleton } from "@/components/ui/Skeleton";
import { layerCredits, loadPhysical, mineralKeyRows, mineralSites, type MineralSite, type MineralsFile, type ReliefFile, type RiversFile } from "@/lib/mapPhysical";
import type { RegionDataset } from "@/lib/regionContract";

export const DRAWING_MINERALS = "Drawing the mineral deposits";
export const NO_EMPHASIS: LayerEmphasis = { layers: [], rivers: [] };

export type LayerParts = { relief: ReactNode; fills: ReactNode; rivers: ReactNode; home: ReactNode };
export type DrawnLayers = { underlay: ReactNode; overlay: (scale: number) => ReactNode; key: ReactNode; parts: LayerParts; credits: RegionDataset[]; files: Physical };
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

export function ReliefUnderOrStill({ file, still, strong = false }: { file: ReliefFile | null; still: MapStill | null; strong?: boolean }) {
  if (file) return <ReliefUnder file={file} strong={strong} />;
  return still?.relief ? <StillRelief still={still} bands={still.relief} /> : null;
}

export function RiversUnderOrStill({ file, still, strength = PLAIN }: { file: RiversFile | null; still: MapStill | null; strength?: Strength }) {
  if (file) return <RiversUnder file={file} strength={strength} />;
  return still?.rivers ? <StillRivers still={still} rivers={still.rivers} lakes={still.lakes} strength={strength} /> : null;
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

function PhysicalOver({ layers, scale, rivers }: { layers: Physical; scale: number; rivers: readonly string[] }) {
  return (
    <>
      {layers.relief ? <ReliefOver file={layers.relief} scale={scale} /> : null}
      {layers.rivers ? <RiversOver file={layers.rivers} named={rivers} /> : null}
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
  const emphasis = names.emphasis ?? NO_EMPHASIS;
  const strength: Strength = { rivers: emphasis.layers.includes("rivers"), water: emphasis.layers.includes("water") };
  const parts: LayerParts = {
    relief: <ReliefUnderOrStill file={relief} still={still} strong={emphasis.layers.includes("relief")} />,
    fills: district.layer.data && district.shapes.data ? <DistrictFills shapes={district.shapes.data} fillOf={fillOf} /> : null,
    rivers: <RiversUnderOrStill file={rivers} still={still} strength={strength} />,
    home: <HomeOrStill shapes={homes} home={names.home} still={still} />
  };
  const underlay = (
    <>
      {parts.relief}
      {parts.fills}
      {parts.rivers}
      {parts.home}
    </>
  );
  const key = (
    <div className="mt-3 grid min-w-0 gap-3" data-testid="timeline-layer-key">
      <PhysicalKey names={names} layers={layers} still={still} />
      {names.district ? <LayerStatus layer={district.layer} shapes={district.shapes} held={still?.district ?? null} /> : null}
    </div>
  );
  const credits = layerCredits([...(relief?.datasets ?? []), ...(rivers?.datasets ?? [])]);
  return { underlay, overlay: (scale) => <PhysicalOver layers={layers} scale={scale} rivers={emphasis.rivers} />, key, parts, credits, files: layers };
}
