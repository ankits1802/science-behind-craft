"use client";

import { useMemo, useState } from "react";

import { IndiaMap } from "@/components/map/IndiaMap";
import type { MapPoint } from "@/components/map/layout";
import { MapAttribution } from "@/components/map/MapAttribution";
import type { PlacedOrigin } from "@/lib/supplyView";

export function SupplyPins({ origins }: { origins: readonly PlacedOrigin[] }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [pinned, setPinned] = useState<string | null>(null);
  const points = useMemo<MapPoint[]>(
    () =>
      origins.map((origin) => ({
        key: origin.key,
        name: origin.origin,
        latitude: origin.place.latitude,
        longitude: origin.place.longitude,
        total: 1,
        pinLabel: String(origin.place.pin),
        countText: origin.material,
        caption: null
      })),
    [origins]
  );
  return (
    <figure className="min-w-0" data-testid="supply-pins">
      <IndiaMap
        points={points}
        hoveredKey={hovered}
        selectedKey={pinned}
        onHover={setHovered}
        onSelect={(key) => setPinned((current) => (current === key ? null : key))}
      />
      <p className="mt-2 text-[11px] leading-4 text-ink-500">Coordinates: Wikidata</p>
      <MapAttribution />
    </figure>
  );
}
