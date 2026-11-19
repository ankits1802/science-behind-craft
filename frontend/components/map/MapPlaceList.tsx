"use client";

import Link from "next/link";

import type { MapPoint } from "@/components/map/layout";
import { cn } from "@/lib/utils";

export interface MapPlaceListProps {
  points: MapPoint[];
  hoveredKey?: string | null;
  selectedKey?: string | null;
  flashKey?: string | null;
  onHover?: (key: string | null) => void;
  registerRow?: (key: string) => (node: HTMLElement | null) => void;
  containerRef?: React.MutableRefObject<HTMLElement | null>;
  countLabel?: (total: number) => string;
  className?: string;
}

function defaultCount(total: number): string {
  return total === 1 ? "1 craft" : `${total} crafts`;
}

function rowClass(active: boolean): string {
  return cn(
    "flex min-h-target items-baseline gap-3 border-t border-rule px-1 py-2 transition-colors duration-state",
    active ? "bg-sunk" : "hover:bg-sunk"
  );
}

export function MapPlaceList({ points, hoveredKey = null, selectedKey = null, flashKey = null, onHover, registerRow, containerRef, countLabel = defaultCount, className }: MapPlaceListProps) {
  return (
    <ol ref={containerRef as React.RefObject<HTMLOListElement>} className={cn("flex flex-col border-b border-rule", className)}>
      {points.map((point, index) => {
        const active = point.key === hoveredKey || point.key === selectedKey;
        const body = (
          <>
            <span className="w-6 shrink-0 text-end font-ui text-label text-ink-3 [font-variant-numeric:tabular-nums]">{index + 1}</span>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-ui text-ui text-ink-1">{point.name}</span>
              {point.caption ? <span className="block truncate font-ui text-caption text-ink-3">{point.caption}</span> : null}
            </span>
            <span className="shrink-0 font-ui text-caption text-ink-3 [font-variant-numeric:tabular-nums]">{countLabel(point.total)}</span>
          </>
        );
        const handlers = {
          onPointerEnter: () => onHover?.(point.key),
          onPointerLeave: () => onHover?.(null),
          onFocus: () => onHover?.(point.key),
          onBlur: () => onHover?.(null)
        };
        return (
          <li key={point.key} ref={registerRow?.(point.key)} data-flash={flashKey === point.key ? "true" : undefined} className="fr-flash-row">
            {point.href ? (
              <Link href={point.href} {...handlers} className={rowClass(active)}>
                {body}
              </Link>
            ) : (
              <div tabIndex={0} {...handlers} className={rowClass(active)}>
                {body}
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
