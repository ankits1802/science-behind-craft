"use client";

import { useCallback, useMemo } from "react";

import { NoSourceFound } from "@/components/craft/ClaimList";
import { RegionPanel } from "@/components/craft/RegionPanel";
import { failureMessage, useRemote, type Remote } from "@/components/hooks/useRemote";
import { DistrictFills, HIGHLIGHT_TONES } from "@/components/map/DistrictLayer";
import { IndiaMapStage } from "@/components/map/IndiaMapStage";
import type { MapPoint } from "@/components/map/layout";
import { loadShapes, type DistrictShape } from "@/components/map/shapeGeometry";
import { RemoteView } from "@/components/RemotePanels";
import { locationCaption } from "@/lib/craftProfile";
import type { CraftRegion } from "@/lib/regionContract";
import { regionHighlight, type RegionHighlight } from "@/lib/regionView";
import type { CraftLocation, CraftProfile } from "@/lib/types";

function locationPoints(locations: readonly CraftLocation[]): MapPoint[] {
  return locations
    .flatMap((location) => (location.latitude !== null && location.longitude !== null ? [{ location, latitude: location.latitude, longitude: location.longitude }] : []))
    .map(({ location, latitude, longitude }, index) => ({
      key: location.id,
      pinLabel: String(index + 1),
      countText: null,
      name: location.placeLabel,
      latitude,
      longitude,
      total: 1,
      caption: locationCaption(location)
    }));
}

function highlightTone(highlight: RegionHighlight, shape: DistrictShape): string | null {
  if (highlight.districts.has(shape.lgd)) return HIGHLIGHT_TONES.district;
  return highlight.states.has(shape.stateLgd) ? HIGHLIGHT_TONES.state : null;
}

export function CraftRegionTab({ profile, region }: { profile: CraftProfile; region: Remote<CraftRegion> }) {
  const points = useMemo(() => locationPoints(profile.locations), [profile.locations]);
  const unplaced = profile.locations.filter((location) => location.latitude === null || location.longitude === null);
  const highlight = useMemo(() => (region.data ? regionHighlight(region.data) : null), [region.data]);
  const shapes = useRemote(highlight && highlight.districts.size + highlight.states.size > 0 ? loadShapes : null);
  const fillOf = useCallback((shape: DistrictShape) => (highlight ? highlightTone(highlight, shape) : null), [highlight]);
  const hasPlaces = profile.locations.length > 0 || (region.data?.places.length ?? 0) > 0;

  if (!hasPlaces && region.data) {
    return (
      <div className="panel p-5">
        <NoSourceFound />
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      {hasPlaces ? (
        <div className="panel p-4 md:p-6">
          <IndiaMapStage
            points={points}
            listLabel="Places"
            countLabel={() => ""}
            layers={{ under: shapes.data ? <DistrictFills shapes={shapes.data} fillOf={fillOf} /> : null }}
          />
          {unplaced.length > 0 ? (
            <ul className="mt-4 grid gap-1 border-t border-line-200 pt-4 text-sm">
              {unplaced.map((location) => (
                <li key={location.id} className="flex flex-wrap items-baseline gap-2">
                  <span className="font-medium text-ink-900">{location.placeLabel}</span>
                  <span className="text-xs text-ink-500">{locationCaption(location)}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
      <RemoteView remote={region} failed={(failure) => failureMessage(failure, "Couldn't load the region.")}>
        {(data) => <RegionPanel region={data} />}
      </RemoteView>
    </div>
  );
}
