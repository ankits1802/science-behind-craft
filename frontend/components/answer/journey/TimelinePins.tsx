"use client";

import { useMemo, useState } from "react";
import { ExternalLink } from "lucide-react";

import { edgePost, inFrame, POST_FONT, POST_HEIGHT } from "@/components/answer/journey/journeyGeometry";
import { useRemote } from "@/components/hooks/useRemote";
import { DistrictFills } from "@/components/map/DistrictLayer";
import { IndiaMap, type MapPoint } from "@/components/map/IndiaMap";
import { MapAttribution } from "@/components/map/MapAttribution";
import { loadShapes } from "@/components/map/shapeGeometry";
import type { BoundaryNote } from "@/lib/regionContract";
import { wikidataUrl } from "@/lib/supplyView";
import type { PlacedPlace, TimelineRouteLine } from "@/lib/timelineView";

const QUIET_TONE = "fill-purple-50 dark:fill-purple-950/40";
const quiet = () => QUIET_TONE;

function RouteLines({ routes }: { routes: readonly TimelineRouteLine[] }) {
  return (
    <g className="pointer-events-none" data-testid="timeline-routes">
      {routes.map((route) => {
        const from = inFrame(route.start.longitude, route.start.latitude);
        const to = inFrame(route.end.longitude, route.end.latitude);
        return (
          <g key={route.key} data-testid="timeline-route">
            <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} className="stroke-purple-700 dark:stroke-purple-300" strokeWidth={3} strokeLinecap="round" vectorEffect="non-scaling-stroke" />
            <circle cx={to.x} cy={to.y} r={7} className="fill-purple-700 stroke-card dark:fill-purple-300" strokeWidth={2} />
          </g>
        );
      })}
    </g>
  );
}

function EdgePosts({ places }: { places: readonly PlacedPlace[] }) {
  return (
    <g className="pointer-events-none" data-testid="timeline-edge-posts">
      {places.map((place) => {
        const text = `${place.pin} ${place.name}`;
        const post = edgePost(place.longitude, place.latitude, text);
        return (
          <g key={place.index} data-testid="timeline-edge-post" data-pin={place.pin} data-angle={post.angle}>
            <rect x={post.left} y={post.top} width={post.width} height={POST_HEIGHT} rx={POST_HEIGHT / 2} className="fill-purple-700 stroke-card" strokeWidth={2} />
            <path d="M -4 -7 L 4 0 L -4 7" transform={`translate(${post.left + 20} ${post.middle}) rotate(${post.angle})`} className="fill-none stroke-white" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
            <text x={post.left + 34} y={post.middle} dominantBaseline="central" fontSize={POST_FONT} className="fill-white font-display font-bold">
              {text}
            </text>
          </g>
        );
      })}
    </g>
  );
}

function PlaceLinks({ placed }: { placed: readonly PlacedPlace[] }) {
  return (
    <ul className="mt-2 flex min-w-0 flex-wrap gap-1.5" aria-label="Places on the map" data-testid="timeline-places">
      {placed.map((place) => (
        <li key={place.index} className="min-w-0">
          <a
            href={wikidataUrl(place.wikidataId)}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-8 max-w-full items-center gap-1.5 rounded-full border border-line-200 bg-surface-50 px-2.5 text-xs text-ink-700 transition hover:border-purple-300 pointer-coarse:min-h-11"
          >
            <span className="font-bold tabular-nums text-purple-700 dark:text-purple-300">{place.pin}</span>
            <span className="min-w-0 break-words font-medium text-ink-900">{place.name}</span>
            <span className="text-ink-500">Wikidata</span>
            <ExternalLink className="h-3 w-3 shrink-0 text-ink-500" aria-hidden />
            <span className="sr-only">(opens in a new tab)</span>
          </a>
        </li>
      ))}
    </ul>
  );
}

export function TimelinePins({
  placed,
  reached,
  routes,
  boundary
}: {
  placed: readonly PlacedPlace[];
  reached: ReadonlySet<number>;
  routes: readonly TimelineRouteLine[];
  boundary: BoundaryNote | null;
}) {
  const shapes = useRemote(loadShapes);
  const [hovered, setHovered] = useState<string | null>(null);
  const [pinned, setPinned] = useState<string | null>(null);
  const shown = useMemo(() => placed.filter((place) => reached.has(place.index)), [placed, reached]);
  const points = useMemo<MapPoint[]>(
    () =>
      shown
        .filter((place) => !place.beyond)
        .map((place) => ({ key: `place:${place.index}`, name: place.name, latitude: place.latitude, longitude: place.longitude, total: 1, pinLabel: String(place.pin), caption: null })),
    [shown]
  );
  const underlay = shapes.data ? <DistrictFills shapes={shapes.data} fillOf={quiet} /> : null;
  const overlay = (
    <>
      <RouteLines routes={routes} />
      <EdgePosts places={shown.filter((place) => place.beyond)} />
    </>
  );
  return (
    <figure className="min-w-0 lg:sticky lg:top-24" data-testid="timeline-pins">
      <IndiaMap
        points={points}
        hoveredKey={hovered}
        selectedKey={pinned}
        onHover={setHovered}
        onSelect={(key) => setPinned((current) => (current === key ? null : key))}
        underlay={underlay}
        overlay={overlay}
      />
      <PlaceLinks placed={placed} />
      <MapAttribution boundary={boundary} />
    </figure>
  );
}
