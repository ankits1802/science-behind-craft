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

export function MapPlaceList({
  points,
  hoveredKey = null,
  selectedKey = null,
  flashKey = null,
  onHover,
  registerRow,
  containerRef,
  countLabel = defaultCount,
  className
}: MapPlaceListProps) {
  return (
    <ol ref={containerRef as React.RefObject<HTMLOListElement>} className={cn("flex flex-col gap-0.5", className)}>
      {points.map((point, index) => {
        const active = point.key === hoveredKey || point.key === selectedKey;
        const rowClass = cn(
          "flex min-h-11 items-baseline gap-3 rounded-md px-3 py-1.5 transition-colors",
          active ? "bg-purple-700/10" : "hover:bg-field-100"
        );
        const body = (
          <>
            <span className="w-6 shrink-0 text-right font-display text-sm font-bold tabular-nums text-purple-700">{index + 1}</span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-ink-900">{point.name}</span>
              {point.caption ? <span className="block truncate text-xs text-ink-500">{point.caption}</span> : null}
            </span>
            <span className="shrink-0 text-xs tabular-nums text-ink-500">{countLabel(point.total)}</span>
          </>
        );
        const handlers = {
          onPointerEnter: () => onHover?.(point.key),
          onPointerLeave: () => onHover?.(null),
          onFocus: () => onHover?.(point.key),
          onBlur: () => onHover?.(null)
        };
        return (
          <li key={point.key} ref={registerRow?.(point.key)} data-flash={flashKey === point.key ? "true" : undefined} className="fr-flash-row rounded-md">
            {point.href ? (
              <Link href={point.href} {...handlers} className={rowClass}>
                {body}
              </Link>
            ) : (
              <div tabIndex={0} {...handlers} className={rowClass}>
                {body}
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
