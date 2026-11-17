"use client";

import { useMemo } from "react";
import { ExternalLink, MapPin } from "lucide-react";

import { lazyBlock } from "@/components/answer/lazyBlock";
import { MapPlaceholder } from "@/components/answer/place/MapPlaceholder";
import { CitedText } from "@/components/answer/ProseBlockView";
import { INDIA_BOUNDS } from "@/components/map/indiaBounds";
import type { SupplyMapBlock } from "@/lib/explainerPlace";
import { placedOrigins, supplyGroups, wikidataUrl, type SupplyGroup, type SupplyOrigin } from "@/lib/supplyView";

const SupplyPins = lazyBlock(() => import("@/components/answer/place/SupplyPins").then((module) => module.SupplyPins), <MapPlaceholder />);

function OriginPill({ origin }: { origin: SupplyOrigin }) {
  return (
    <li className="inline-flex min-h-8 max-w-full items-center gap-1.5 rounded-full border border-line-200 bg-surface-50 px-2.5 text-sm text-ink-900" data-testid="supply-origin">
      {origin.place ? (
        <span className="inline-flex items-center gap-0.5 text-xs font-bold tabular-nums text-purple-700 dark:text-purple-300" data-testid="supply-pin">
          <MapPin className="h-3.5 w-3.5" aria-hidden />
          {origin.place.pin}
        </span>
      ) : null}
      <span className="min-w-0 break-words font-medium">{origin.origin}</span>
      {origin.wikidataId ? (
        <a
          href={wikidataUrl(origin.wikidataId)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex shrink-0 items-center gap-0.5 text-[11px] text-ink-500 underline-offset-2 hover:text-purple-700 hover:underline"
        >
          Wikidata
          <ExternalLink className="h-3 w-3" aria-hidden />
        </a>
      ) : null}
    </li>
  );
}

function MaterialCard({ group }: { group: SupplyGroup }) {
  return (
    <li className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2 rounded-lg border border-line-200 bg-card p-3 sm:p-4" data-testid="supply-material">
      <h3 className="font-display text-base font-bold text-ink-900">{group.material}</h3>
      <ul className="flex min-w-0 flex-wrap gap-1.5" aria-label={`Where ${group.material} comes from`}>
        {group.origins.map((origin) => (
          <OriginPill key={origin.key} origin={origin} />
        ))}
      </ul>
      {group.sentences.map((sentence) => (
        <CitedText key={sentence.id} id={sentence.id} sentences={[sentence]} className="text-sm leading-7 text-ink-700" />
      ))}
    </li>
  );
}

export function SupplyMapView({ block }: { block: SupplyMapBlock }) {
  const groups = useMemo(() => supplyGroups(block, INDIA_BOUNDS), [block]);
  const placed = useMemo(() => placedOrigins(groups), [groups]);
  return (
    <div className={placed.length > 0 ? "grid min-w-0 grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-start" : "min-w-0"} data-testid="supply-map">
      <ul className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2.5">
        {groups.map((group) => (
          <MaterialCard key={group.key} group={group} />
        ))}
      </ul>
      {placed.length > 0 ? <SupplyPins origins={placed} /> : null}
    </div>
  );
}
