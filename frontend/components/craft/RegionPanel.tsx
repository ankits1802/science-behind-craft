"use client";

import { useMemo } from "react";

import { RegionPlaceCard } from "@/components/craft/RegionPlaceCard";
import { DatasetCredit } from "@/components/DatasetCredit";
import type { CraftRegion } from "@/lib/regionContract";
import { datasetIndex, datasetMethods } from "@/lib/regionView";

export function RegionPanel({ region }: { region: CraftRegion }) {
  const datasets = useMemo(() => datasetIndex(region.datasets), [region]);
  const methods = useMemo(() => datasetMethods(region), [region]);
  if (region.places.length === 0) return null;
  return (
    <div className="grid gap-3" data-testid="region-panel">
      {region.places.map((place) => (
        <RegionPlaceCard key={place.key} place={place} datasets={datasets} />
      ))}
      {region.datasets.length > 0 ? (
        <section aria-labelledby="region-data-heading" className="panel p-4 md:p-5">
          <h3 id="region-data-heading" className="field-label">
            Data
          </h3>
          <ul className="mt-3 grid gap-3">
            {region.datasets.map((dataset) => (
              <li key={dataset.code}>
                <DatasetCredit dataset={dataset} methods={methods.get(dataset.code) ?? []} />
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
