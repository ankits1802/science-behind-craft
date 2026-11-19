"use client";

import { Suspense, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { CitedReading, ListedSources } from "@/components/answer/CitedReading";
import { CompareTable } from "@/components/answer/learning/CompareTable";
import { failureMessage, useRemote } from "@/components/hooks/useRemote";
import { ComparePicker } from "@/components/learn/ComparePicker";
import { MapRetry } from "@/components/map/MapRetry";
import { Skeleton } from "@/components/ui/Skeleton";
import { craftOptions, DETECT_CRAFT } from "@/lib/askCraft";
import { listedSourceNumbers } from "@/lib/citations";
import { comparable, compareHref, comparedSlugs, compareState, COMPARE_PARAM, NOTHING_CITED, UNKNOWN_CRAFT } from "@/lib/comparePage";
import type { CraftComparison } from "@/lib/compareContract";
import { useCraftCatalogue } from "@/lib/craftCatalogue";
import { fetchComparison } from "@/lib/learningApi";

const COMPARE_FAILED = "The comparison could not be drawn. Try again in a moment.";
const NOTE = "border-t border-rule pt-4 font-ui text-ui font-normal text-ink-2";

export default function ComparePage() {
  return (
    <Suspense fallback={null}>
      <CompareScreen />
    </Suspense>
  );
}

function Comparison({ comparison }: { comparison: CraftComparison }) {
  const numbers = useMemo(() => listedSourceNumbers(comparison.sources), [comparison]);
  return (
    <CitedReading sources={comparison.sources} numbers={numbers}>
      <section className="min-w-0 border-t border-ink-1 pt-4" data-testid="comparison">
        <CompareTable block={comparison.comparison} />
      </section>
      <ListedSources sources={comparison.sources} idPrefix="compare-source" />
    </CitedReading>
  );
}

function CompareHeader() {
  return (
    <header className="grid gap-3 pt-6">
      <p className="kicker">The atlas</p>
      <h1 className="font-headline text-h1 text-ink-1">Compare crafts</h1>
      <p className="max-w-[52ch] font-reading text-lede text-ink-2">Choose two to four crafts to set their cited science side by side.</p>
    </header>
  );
}

function CompareScreen() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { catalogue } = useCraftCatalogue();
  const slugs = useMemo(() => comparedSlugs(params.getAll(COMPARE_PARAM)), [params]);
  const load = useMemo(() => (comparable(slugs) ? () => fetchComparison(slugs) : null), [slugs]);
  const comparison = useRemote(load);
  const options = useMemo(() => craftOptions(catalogue, DETECT_CRAFT, null), [catalogue]);
  const choose = (next: string[]) => router.replace(next.length > 0 ? compareHref(next) : pathname, { scroll: false });
  const state = compareState(load !== null, comparison.data, comparison.failure?.cause ?? null);

  return (
    <div className="grid min-w-0 gap-8 pb-section">
      <CompareHeader />
      <ComparePicker slugs={slugs} options={options} onChange={choose} />
      {state === "unknown" && comparison.failure ? (
        <p className={NOTE} data-testid="compare-unknown">
          {failureMessage(comparison.failure, UNKNOWN_CRAFT)}
        </p>
      ) : null}
      {state === "failed" && comparison.failure ? <MapRetry message={failureMessage(comparison.failure, COMPARE_FAILED)} onRetry={comparison.retry} /> : null}
      {state === "shown" && comparison.data?.comparison ? <Comparison comparison={comparison.data.comparison} /> : null}
      {state === "empty" ? (
        <p className={NOTE} data-testid="compare-empty">
          {NOTHING_CITED}
        </p>
      ) : null}
      {state === "loading" ? <Skeleton shape="chart" label="Setting the crafts side by side" /> : null}
    </div>
  );
}
