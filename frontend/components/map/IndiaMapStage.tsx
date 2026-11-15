"use client";

import { useEffect, useState } from "react";

import { useRevealRow } from "@/components/hooks/useRevealRow";
import { IndiaMap } from "@/components/map/IndiaMap";
import type { MapPoint } from "@/components/map/layout";
import { MapAttribution } from "@/components/map/MapAttribution";
import { MapPlaceList } from "@/components/map/MapPlaceList";
import { cn } from "@/lib/utils";

export function IndiaMapStage({
  points,
  countLabel,
  listLabel,
  districtsIndicative = true,
  className
}: {
  points: MapPoint[];
  countLabel?: (total: number) => string;
  listLabel: string;
  districtsIndicative?: boolean;
  className?: string;
}) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);
  const [pinnedKey, setPinnedKey] = useState<string | null>(null);
  const [pendingReveal, setPendingReveal] = useState<{ key: string; nonce: number } | null>(null);
  const { registerRow, containerRef, reveal, flashKey } = useRevealRow();

  useEffect(() => {
    if (pendingReveal) reveal(pendingReveal.key);
  }, [pendingReveal, reveal]);

  return (
    <div className={cn("grid items-start gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] lg:gap-10", className)}>
      <figure className="min-w-0">
        <IndiaMap
          points={points}
          hoveredKey={hoveredKey}
          selectedKey={pinnedKey}
          onHover={setHoveredKey}
          onSelect={(key) => {
            setPinnedKey((current) => (current === key ? null : key));
            setPendingReveal((current) => ({ key, nonce: (current?.nonce ?? 0) + 1 }));
          }}
        />
        <MapAttribution districtsIndicative={districtsIndicative} />
      </figure>
      <section aria-label={listLabel} className="min-w-0">
        <MapPlaceList
          points={points}
          hoveredKey={hoveredKey}
          selectedKey={pinnedKey}
          flashKey={flashKey}
          onHover={setHoveredKey}
          registerRow={registerRow}
          containerRef={containerRef}
          countLabel={countLabel}
          className="lg:sticky lg:top-24 lg:max-h-[calc(100dvh-7.5rem)] lg:overflow-y-auto lg:overscroll-contain"
        />
      </section>
    </div>
  );
}
