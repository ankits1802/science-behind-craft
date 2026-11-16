"use client";

import { Droplets, Gem, Layers, Mountain, Sprout, Thermometer, Trees, type LucideIcon } from "lucide-react";

import { EvidenceLevelBadge } from "@/components/answer/EvidenceBadge";
import { useCitations } from "@/components/craft/CitationContext";
import { sourceHref } from "@/lib/citations";
import type { PlaceBasis, RegionDataset, RegionFacet, RegionFacetName, RegionPlace } from "@/lib/regionContract";
import { datasetOf, FACET_LABEL, inheritedNote, placeSubtitle, shownFacets, valueLabel, valueProvenance, valueReading } from "@/lib/regionView";

const FACET_ICON: Record<RegionFacetName, LucideIcon> = {
  SOIL: Sprout,
  CLIMATE: Thermometer,
  WATER: Droplets,
  FOREST: Trees,
  LAND_COVER: Layers,
  TERRAIN: Mountain,
  GEOLOGY: Gem
};

export function RegionPlaceCard({ place, datasets }: { place: RegionPlace; datasets: Map<string, RegionDataset> }) {
  const note = inheritedNote(place);
  const facets = shownFacets(place);
  return (
    <article className="panel p-4 md:p-5" data-testid="region-place" data-values-from={place.valuesFrom}>
      <header className="grid gap-1">
        <h3 className="font-display text-base font-bold text-ink-900">{place.placeLabel}</h3>
        <p className="text-xs font-medium text-ink-500">{placeSubtitle(place)}</p>
        <BasisLine basis={place.basis} />
      </header>
      {note ? <p className="mt-3 rounded-md bg-surface-50 px-3 py-2 text-xs leading-5 text-ink-700 ring-1 ring-line-200">{note}</p> : null}
      {facets.length > 0 ? (
        <div className="mt-4 grid gap-x-8 gap-y-5 md:grid-cols-2">
          {facets.map((facet) => (
            <FacetBlock key={facet.facet} facet={facet} datasets={datasets} />
          ))}
        </div>
      ) : null}
    </article>
  );
}

function BasisLine({ basis }: { basis: PlaceBasis }) {
  const { numbers, sourcesById } = useCitations();
  const source = basis.sourceId ? sourcesById.get(basis.sourceId) : undefined;
  const href = source ? sourceHref(source) : null;
  const number = basis.sourceId ? numbers.get(basis.sourceId) : undefined;
  return (
    <p className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-ink-500">
      <span>Source:</span>
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer" className="text-ink-700 underline-offset-2 hover:text-purple-700 hover:underline dark:hover:text-purple-300">
          {basis.label}
        </a>
      ) : (
        <span className="text-ink-700">{basis.label}</span>
      )}
      {number ? <span className="font-display font-bold tabular-nums text-purple-700 dark:text-purple-300">[{number}]</span> : null}
      <EvidenceLevelBadge level={basis.level} />
    </p>
  );
}

function FacetBlock({ facet, datasets }: { facet: RegionFacet; datasets: Map<string, RegionDataset> }) {
  const Icon = FACET_ICON[facet.facet];
  return (
    <section data-testid={`region-facet-${facet.facet}`}>
      <h4 className="field-label mb-2 flex items-center gap-1.5">
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {FACET_LABEL[facet.facet]}
      </h4>
      <dl className="grid gap-3">
        {facet.values.map((value, index) => (
          <div key={`${value.datasetCode}:${value.variable}:${value.depth ?? ""}:${value.period}:${value.stat}:${index}`} className="grid gap-0.5">
            <dt className="text-xs text-ink-500">{valueLabel(value)}</dt>
            <dd className="text-[15px] font-semibold tabular-nums text-ink-900">{valueReading(value)}</dd>
            <dd className="text-[11px] leading-4 text-ink-500">{valueProvenance(value, datasetOf(datasets, value.datasetCode))}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
