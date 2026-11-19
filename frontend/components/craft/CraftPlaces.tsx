"use client";

import { MapPin, Users } from "lucide-react";

import { ClaimChips } from "@/components/craft/CraftClaims";
import type { PageCommunity, PagePlace } from "@/lib/craftPageContract";
import { GROUP_KIND_LABEL, MAKING_ROLES, PLACE_KIND_LABEL, PLACE_ROLE_LABEL, placeRows } from "@/lib/craftPlaces";
import { cn } from "@/lib/utils";

const ROLE_CHIP = "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold";

export function CraftPlaces({ places }: { places: readonly PagePlace[] }) {
  if (places.length === 0) return null;
  return (
    <section aria-labelledby="craft-places-heading" className="panel p-5 md:p-6" data-testid="craft-places">
      <h2 id="craft-places-heading" className="font-display text-lg font-bold text-ink-900">
        Places
      </h2>
      <ul className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        {placeRows(places).map((row) => (
          <li key={row.key} className="grid min-w-0 grid-cols-[1.25rem_minmax(0,1fr)] gap-x-2 rounded-md border border-line-200 bg-surface-50 p-3" data-testid="craft-place">
            <MapPin className="mt-0.5 h-4 w-4 text-purple-700 dark:text-purple-300" aria-hidden />
            <div className="min-w-0">
              <p className="text-sm font-semibold text-ink-900 [overflow-wrap:anywhere]">
                {row.name}
                <ClaimChips ids={row.claimIds} />
              </p>
              <p className="text-xs text-ink-500">{[PLACE_KIND_LABEL[row.kind], row.where].join(" · ")}</p>
              <p className="mt-2 flex flex-wrap gap-1.5">
                {row.roles.map((role) => (
                  <span
                    key={role}
                    data-role={role}
                    className={cn(ROLE_CHIP, MAKING_ROLES.has(role) ? "border-purple-300 bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300" : "border-line-200 bg-card text-ink-700")}
                  >
                    {PLACE_ROLE_LABEL[role]}
                  </span>
                ))}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function CraftCommunities({ communities }: { communities: readonly PageCommunity[] }) {
  if (communities.length === 0) return null;
  return (
    <section aria-labelledby="craft-people-heading" className="panel p-5 md:p-6" data-testid="craft-communities">
      <h2 id="craft-people-heading" className="font-display text-lg font-bold text-ink-900">
        People and groups
      </h2>
      <ul className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        {communities.map((group) => (
          <li key={group.key} className="grid min-w-0 grid-cols-[1.25rem_minmax(0,1fr)] gap-x-2" data-testid="craft-community">
            <Users className="mt-0.5 h-4 w-4 text-ink-500" aria-hidden />
            <div className="min-w-0">
              <p className="text-sm font-semibold text-ink-900 [overflow-wrap:anywhere]">
                {group.name}
                <ClaimChips ids={group.claimIds} />
              </p>
              <p className="text-xs text-ink-500 [overflow-wrap:anywhere]">{[GROUP_KIND_LABEL[group.kind], group.place, ...group.localNames].filter(Boolean).join(" · ")}</p>
              {group.honours.length > 0 ? <p className="mt-1 text-xs text-ink-700 [overflow-wrap:anywhere]">{group.honours.join(" · ")}</p> : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
