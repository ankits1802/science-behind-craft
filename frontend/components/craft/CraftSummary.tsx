"use client";

import { CitedProse, ClaimChips } from "@/components/craft/CraftClaims";
import type { KeyFact, PageSentence } from "@/lib/craftPageContract";
import type { RegisterFact } from "@/lib/craftPageView";

function FactList({ facts, testId }: { facts: readonly (KeyFact | RegisterFact)[]; testId: string }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2 xl:grid-cols-4" data-testid={testId}>
      {facts.map((fact) => (
        <div key={fact.label} className="min-w-0 border-t border-line-200 pt-3" data-testid="craft-fact">
          <dt className="field-label">{fact.label}</dt>
          <dd className="mt-1 text-sm font-medium leading-6 text-ink-900 [overflow-wrap:anywhere]">
            {fact.value}
            {"claimIds" in fact ? <ClaimChips ids={fact.claimIds} /> : null}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function CraftSummary({ lede, keyFacts }: { lede: readonly PageSentence[]; keyFacts: readonly KeyFact[] }) {
  if (lede.length + keyFacts.length === 0) return null;
  return (
    <section aria-label="Summary" className="panel grid gap-5 p-5 md:p-6">
      {lede.length > 0 ? (
        <div className="max-w-3xl" data-testid="craft-lede">
          <CitedProse sentences={lede} tone="lede" />
        </div>
      ) : null}
      {keyFacts.length > 0 ? <FactList facts={keyFacts} testId="craft-key-facts" /> : null}
    </section>
  );
}

export function CraftRegister({ facts }: { facts: readonly RegisterFact[] }) {
  if (facts.length === 0) return null;
  return (
    <section aria-label="At a glance" className="panel p-5 md:p-6">
      <FactList facts={facts} testId="craft-register" />
    </section>
  );
}
