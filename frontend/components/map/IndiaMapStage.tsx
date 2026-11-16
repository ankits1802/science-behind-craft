"use client";

import { useEffect, useState, type ReactNode } from "react";

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
  layers,
  footer,
  className
}: {
  points: MapPoint[];
  countLabel?: (total: number) => string;
  listLabel: string;
  layers?: { under?: ReactNode; over?: ReactNode };
  footer?: ReactNode;
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
    <div className={cn("grid items-start gap-6 lg:gap-10", points.length > 0 && "lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]", className)}>
      <figure className="min-w-0">
        <IndiaMap
          points={points}
          hoveredKey={hoveredKey}
          selectedKey={pinnedKey}
          onHover={setHoveredKey}
          underlay={layers?.under}
          overlay={layers?.over}
          onSelect={(key) => {
            setPinnedKey((current) => (current === key ? null : key));
            setPendingReveal((current) => ({ key, nonce: (current?.nonce ?? 0) + 1 }));
          }}
        />
        {footer ?? <MapAttribution />}
      </figure>
      {points.length > 0 ? (
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
      ) : null}
    </div>
  );
}
