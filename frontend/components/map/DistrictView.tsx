"use client";

import Link from "next/link";
import { GitCompareArrows, X } from "lucide-react";

import { ListedSources } from "@/components/answer/CitedReading";
import { ExplainerBlockView } from "@/components/answer/ExplainerBlockView";
import { BasisLine, FacetBlock } from "@/components/craft/RegionPlaceCard";
import { DatasetCredit } from "@/components/DatasetCredit";
import { compareHref, COMPARE_CRAFTS_MAX } from "@/lib/comparePage";
import { PLACE_ROLE_LABEL } from "@/lib/craftPlaces";
import type { DistrictCraft, DistrictCrafts } from "@/lib/districtCraftsContract";
import { craftsHeading, districtTitle } from "@/lib/districtView";
import { datasetIndex } from "@/lib/regionView";

function CraftRow({ entry }: { entry: DistrictCraft }) {
  return (
    <li className="grid min-w-0 gap-1 rounded-md border border-line-200 bg-card p-3" data-testid="district-craft">
      <Link href={entry.craft.path} className="min-w-0 break-words font-display text-base font-bold text-purple-700 underline-offset-2 hover:underline dark:text-purple-300">
        {entry.craft.name}
      </Link>
      <p className="text-xs font-medium text-ink-700">{entry.roles.map((role) => PLACE_ROLE_LABEL[role]).join(" · ")}</p>
      <BasisLine basis={entry.basis} />
    </li>
  );
}

function LandStory({ district, reduce }: { district: DistrictCrafts; reduce: boolean }) {
  const land = district.land;
  if (!land) return null;
  const datasets = datasetIndex(district.datasets);
  return (
    <section aria-labelledby="district-land" className="grid min-w-0 gap-4" data-testid="district-land">
      <h3 id="district-land" className="font-display text-base font-bold text-ink-900">
        Why the land suits them
      </h3>
      {land.blocks.map((block) => (
        <ExplainerBlockView key={block.id} block={block} reduce={reduce} />
      ))}
      {land.facets.length > 0 ? (
        <div className="grid min-w-0 gap-x-8 gap-y-5 md:grid-cols-2">
          {land.facets.map((facet) => (
            <FacetBlock key={facet.facet} facet={facet} datasets={datasets} />
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function DistrictView({ district, reduce, onClose }: { district: DistrictCrafts; reduce: boolean; onClose: () => void }) {
  const compare = district.crafts.length >= 2 ? compareHref(district.crafts.slice(0, COMPARE_CRAFTS_MAX).map((entry) => entry.craft.slug)) : null;
  return (
    <article className="grid min-w-0 gap-5" data-testid="district-view" data-lgd={district.district.districtLgd}>
      <header className="flex min-w-0 items-start justify-between gap-3">
        <div className="grid min-w-0 gap-0.5">
          <p className="eyebrow">Selected district</p>
          <h2 className="break-words font-display text-xl font-bold text-ink-900">{districtTitle(district.district)}</h2>
        </div>
        <button type="button" onClick={onClose} aria-label="Close the district" className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-line-200 bg-card text-ink-700 hover:bg-surface-50 pointer-coarse:h-11 pointer-coarse:w-11">
          <X className="h-4 w-4" aria-hidden />
        </button>
      </header>
      <section aria-labelledby="district-crafts" className="grid min-w-0 gap-3">
        <h3 id="district-crafts" className="font-display text-base font-bold text-ink-900">
          {craftsHeading(district.crafts.length)}
        </h3>
        {district.crafts.length > 0 ? (
          <ul className="grid min-w-0 gap-2 sm:grid-cols-2">
            {district.crafts.map((entry) => (
              <CraftRow key={entry.craft.slug} entry={entry} />
            ))}
          </ul>
        ) : null}
        {compare ? (
          <Link href={compare} className="field-button-secondary w-fit max-w-full rounded-full">
            <GitCompareArrows className="h-4 w-4 shrink-0" aria-hidden />
            Compare these crafts
          </Link>
        ) : null}
      </section>
      <LandStory district={district} reduce={reduce} />
      <ListedSources sources={district.sources} idPrefix="district-source" />
      <footer className="grid min-w-0 gap-2" data-testid="district-credits">
        {district.datasets.map((dataset) => (
          <DatasetCredit key={dataset.code} dataset={dataset} />
        ))}
        <p className="text-[11px] leading-4 text-ink-500" data-testid="district-boundary">
          {district.boundaryCaption}
        </p>
      </footer>
    </article>
  );
}
