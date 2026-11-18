"use client";

import type { StoryLayer } from "@/components/answer/place/useStoryLayer";
import type { Remote } from "@/components/hooks/useRemote";
import { ChoroplethLegend } from "@/components/map/ChoroplethLegend";
import { LayerStatus } from "@/components/map/MapLayerView";
import type { DistrictShape } from "@/components/map/shapeGeometry";
import type { RegionStoryBlock } from "@/lib/explainerPlace";
import type { MapLayer } from "@/lib/regionContract";
import { districtReading } from "@/lib/regionView";

export function storyScopeNote(shown: MapLayer): string {
  const count = Object.keys(shown.values).length;
  return `Shades compare the ${count} ${count === 1 ? "district" : "districts"} on this map.`;
}

export function StoryReadings({ block, layer }: { block: RegionStoryBlock; layer: MapLayer }) {
  return (
    <ul className="mt-3 grid min-w-0 grid-cols-[minmax(0,1fr)] gap-1 text-xs text-ink-700 sm:grid-cols-[repeat(2,minmax(0,1fr))]" aria-label={`${layer.layer.title} by district`} data-testid="story-readings">
      {block.districts.map((district) => (
        <li key={district.districtLgd} className="flex min-w-0 items-baseline justify-between gap-2 border-b border-line-200 py-1">
          <span className="min-w-0 break-words font-semibold text-ink-900">{district.name}</span>
          <span className="shrink-0 tabular-nums">{districtReading(layer, district.districtLgd)}</span>
        </li>
      ))}
    </ul>
  );
}

export function StoryLayerReadout({ block, story, shown, shapes }: { block: RegionStoryBlock; story: StoryLayer; shown: MapLayer | null; shapes: Remote<DistrictShape[]> }) {
  if (!story.chosen) return null;
  const national = story.layer.data;
  if (shown && national && shapes.data) {
    return (
      <>
        <StoryReadings block={block} layer={national} />
        <ChoroplethLegend layer={shown} note={storyScopeNote(shown)} />
      </>
    );
  }
  if (national && shapes.data) {
    return (
      <p role="status" className="mt-4 border-t border-line-200 pt-4 text-sm text-ink-500" data-testid="story-layer-empty">
        No district on this map has a reading for {national.layer.title.toLowerCase()}.
      </p>
    );
  }
  return <LayerStatus layer={story.layer} shapes={shapes} />;
}
