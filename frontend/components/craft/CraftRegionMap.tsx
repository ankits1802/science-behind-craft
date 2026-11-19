"use client";

import { useCallback, useMemo } from "react";

import { useRemote } from "@/components/hooks/useRemote";
import { DistrictFills, DistrictTag, HIGHLIGHT_TONES } from "@/components/map/DistrictLayer";
import { IndiaMapStage } from "@/components/map/IndiaMapStage";
import { loadShapes, type DistrictShape } from "@/components/map/shapeGeometry";
import type { PagePlace } from "@/lib/craftPageContract";
import { placeDistricts } from "@/lib/craftPlaces";
import type { CraftRegion } from "@/lib/regionContract";
import { regionHighlight } from "@/lib/regionView";

const NO_POINTS: never[] = [];

export function CraftRegionMap({ places, region }: { places: readonly PagePlace[]; region: CraftRegion | null }) {
  const districts = useMemo(() => placeDistricts(places), [places]);
  const highlight = useMemo(() => (region ? regionHighlight(region) : null), [region]);
  const wanted = districts.named.size > 0 || (highlight !== null && highlight.districts.size + highlight.states.size > 0);
  const shapes = useRemote(wanted ? loadShapes : null);
  const fillOf = useCallback(
    (shape: DistrictShape) => {
      if (districts.made.has(shape.lgd) || highlight?.districts.has(shape.lgd)) return HIGHLIGHT_TONES.district;
      return highlight?.states.has(shape.stateLgd) ? HIGHLIGHT_TONES.state : null;
    },
    [districts, highlight]
  );
  const tagged = (shapes.data ?? []).filter((shape) => districts.named.has(shape.lgd));
  return (
    <div className="panel p-4 md:p-6" data-testid="craft-region-map">
      <IndiaMapStage
        points={NO_POINTS}
        listLabel="Places"
        layers={{
          under: shapes.data ? <DistrictFills shapes={shapes.data} fillOf={fillOf} /> : null,
          over: tagged.map((shape) => <DistrictTag key={shape.lgd} shape={shape} text={districts.named.get(shape.lgd) ?? ""} />)
        }}
      />
    </div>
  );
}
