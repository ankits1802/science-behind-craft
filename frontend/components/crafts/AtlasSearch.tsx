"use client";

import { useDeferredValue, useMemo } from "react";

import { ConceptGroup, CraftMatches } from "@/components/crafts/ConceptMatches";
import { SearchInput } from "@/components/SearchInput";
import { Chip } from "@/components/ui/Chip";
import { SEARCH_ANCHOR, tryQueries } from "@/lib/atlasIndex";
import { CONCEPT_GROUPS_SHOWN, searchStatus } from "@/lib/atlasSearch";
import { craftIndex, craftSearchScore, foldCraftText, searchCatalogue } from "@/lib/craftCatalogue";
import type { CraftCatalogue } from "@/lib/craftCatalogueContract";

export const SEARCH_LABEL = "Search crafts, places and the science behind them";

function TryChips({ catalogue, query, onQuery }: { catalogue: CraftCatalogue; query: string; onQuery: (query: string) => void }) {
  const tries = useMemo(() => tryQueries(catalogue), [catalogue]);
  if (!tries.length) return null;
  const folded = foldCraftText(query);
  return (
    <p className="mt-3 flex flex-wrap items-center gap-2 font-ui text-label font-normal text-ink-3">
      <span>Try</span>
      {tries.map((term) => (
        <Chip key={term} pressed={foldCraftText(term) === folded} onClick={() => onQuery(term)}>
          {term}
        </Chip>
      ))}
    </p>
  );
}

export function AtlasSearchBox({ catalogue, query, onQuery }: { catalogue: CraftCatalogue | null; query: string; onQuery: (query: string) => void }) {
  return (
    <div id={SEARCH_ANCHOR} className="min-w-0 scroll-mt-24">
      <p className="mb-2 font-ui text-label text-ink-2">{SEARCH_LABEL}</p>
      <SearchInput value={query} onChange={onQuery} placeholder="indigo, Kachchh, lost wax" ariaLabel={SEARCH_LABEL} shortcut />
      {catalogue ? <TryChips catalogue={catalogue} query={query} onQuery={onQuery} /> : null}
    </div>
  );
}

export function AtlasResults({ catalogue, query, onQuery }: { catalogue: CraftCatalogue; query: string; onQuery: (query: string) => void }) {
  const deferred = useDeferredValue(query);
  const found = useMemo(() => searchCatalogue(catalogue, deferred), [catalogue, deferred]);
  const direct = useMemo(() => {
    if (!foldCraftText(deferred)) return [];
    const index = craftIndex(catalogue);
    return found.crafts.filter((craft) => !craft.isCatchAll && craftSearchScore(index, craft, deferred) !== null);
  }, [catalogue, deferred, found]);
  const concepts = found.concepts.slice(0, CONCEPT_GROUPS_SHOWN);
  const status = searchStatus(deferred, concepts.length, concepts[0]?.crafts.length ?? direct.length, concepts[0]?.concept.label ?? null);
  const shown = concepts.length > 0 || direct.length > 0;
  return (
    <>
      <p className="sr-only" role="status" data-testid="craft-count">
        {status}
      </p>
      {shown ? (
        <div className="mt-3 border-t border-ink-1" data-testid="atlas-results">
          {concepts.map((hit) => (
            <ConceptGroup key={hit.concept.key} hit={hit} catalogue={catalogue} onQuery={onQuery} />
          ))}
          <CraftMatches crafts={direct} catalogue={catalogue} />
        </div>
      ) : deferred.trim() ? (
        <p className="mt-3 border-t border-ink-1 pt-4 font-ui text-ui font-normal text-ink-2" data-testid="atlas-no-match">
          Search finds crafts by their name, their state or a material named in their sources. Try one of the words above.
        </p>
      ) : null}
    </>
  );
}
