"use client";

import { Suspense, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { GitCompareArrows } from "lucide-react";

import { CitedReading, ListedSources } from "@/components/answer/CitedReading";
import { CompareTable } from "@/components/answer/learning/CompareTable";
import { failureMessage, useRemote } from "@/components/hooks/useRemote";
import { ComparePicker } from "@/components/learn/ComparePicker";
import { PageHeader } from "@/components/PageHeader";
import { LoadingPanel, RetryPanel } from "@/components/RemotePanels";
import { craftOptions, DETECT_CRAFT } from "@/lib/askCraft";
import { listedSourceNumbers } from "@/lib/citations";
import { comparable, compareHref, comparedSlugs, compareState, COMPARE_PARAM, NOTHING_CITED, UNKNOWN_CRAFT } from "@/lib/comparePage";
import type { CraftComparison } from "@/lib/compareContract";
import { useCraftCatalogue } from "@/lib/craftCatalogue";
import { fetchComparison } from "@/lib/learningApi";

const COMPARE_FAILED = "Couldn't compare these crafts.";

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
      <section className="panel min-w-0 p-4 md:p-6" data-testid="comparison">
        <CompareTable block={comparison.comparison} />
      </section>
      <ListedSources sources={comparison.sources} idPrefix="compare-source" />
    </CitedReading>
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
    <>
      <PageHeader title="Compare crafts" icon={<GitCompareArrows className="h-5 w-5" aria-hidden />} />
      <div className="grid min-w-0 gap-5">
        <ComparePicker slugs={slugs} options={options} onChange={choose} />
        {state === "unknown" && comparison.failure ? (
          <p className="panel p-5 text-sm text-ink-700" data-testid="compare-unknown">
            {failureMessage(comparison.failure, UNKNOWN_CRAFT)}
          </p>
        ) : null}
        {state === "failed" && comparison.failure ? <RetryPanel message={failureMessage(comparison.failure, COMPARE_FAILED)} onRetry={comparison.retry} /> : null}
        {state === "shown" && comparison.data?.comparison ? <Comparison comparison={comparison.data.comparison} /> : null}
        {state === "empty" ? (
          <p className="panel p-5 text-sm text-ink-700" data-testid="compare-empty">
            {NOTHING_CITED}
          </p>
        ) : null}
        {state === "loading" ? <LoadingPanel /> : null}
      </div>
    </>
  );
}
