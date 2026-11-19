"use client";

import { ContributedPlates } from "@/components/craft/ContributedPlates";
import { CraftCommunities, CraftPlaces } from "@/components/craft/CraftPlaces";
import { CraftRegionMap } from "@/components/craft/CraftRegionMap";
import { RegionPanel } from "@/components/craft/RegionPanel";
import { failureMessage, type Remote } from "@/components/hooks/useRemote";
import { RemoteView } from "@/components/RemotePanels";
import { NO_PLATES, type ContributedPlate } from "@/lib/craftContributed";
import type { CraftPage, PagePlace } from "@/lib/craftPageContract";
import type { CraftRegion } from "@/lib/regionContract";

function Environment({ region, places }: { region: CraftRegion; places: readonly PagePlace[] }) {
  if (region.places.length === 0) return null;
  return (
    <section aria-labelledby="craft-environment-heading" className="grid gap-3">
      <h2 id="craft-environment-heading" className="mt-2 font-display text-lg font-bold text-ink-900">
        Land, water and climate
      </h2>
      <RegionPanel region={region} places={places} />
    </section>
  );
}

export function CraftRegionTab({ page, region, contributed = NO_PLATES }: { page: CraftPage; region: Remote<CraftRegion>; contributed?: readonly ContributedPlate[] }) {
  return (
    <div className="grid gap-4">
      <CraftRegionMap places={page.places} region={region.data} />
      <CraftPlaces places={page.places} />
      <CraftCommunities communities={page.communities} />
      <ContributedPlates plates={contributed} />
      <RemoteView remote={region} failed={(failure) => failureMessage(failure, "Couldn't load the region.")}>
        {(data) => <Environment region={data} places={page.places} />}
      </RemoteView>
    </div>
  );
}
