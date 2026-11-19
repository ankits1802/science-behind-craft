"use client";

import { useRouter } from "next/navigation";

import type { MapScene } from "@/components/map/MapCanvas";
import { project } from "@/components/map/projection";
import type { PlaceMarker } from "@/lib/mapFamilies";

export const MARKER_PX = 4.5;

export function PlaceMarkers({ markers, scene }: { markers: readonly PlaceMarker[]; scene: MapScene }) {
  const router = useRouter();
  const radius = MARKER_PX * scene.scale;
  return (
    <g data-testid="place-markers">
      {markers.map((marker) => {
        const at = project(marker.longitude, marker.latitude);
        return (
          <circle
            key={marker.key}
            cx={at.x}
            cy={at.y}
            r={radius}
            fill={marker.family ? marker.family.colour : "var(--map-marker)"}
            stroke="var(--map-marker-ring)"
            strokeWidth={1.5}
            vectorEffect="non-scaling-stroke"
            className="cursor-pointer"
            onClick={() => router.push(marker.href)}
            data-testid="place-marker"
          >
            <title>{`${marker.name}: ${marker.crafts.join(", ")}`}</title>
          </circle>
        );
      })}
    </g>
  );
}
