"use client";

import { useExplainerReading } from "@/components/answer/ExplainerReading";
import { TERM_CLASS } from "@/components/answer/ExplainerSentence";
import { ClaimChips } from "@/components/craft/CraftClaims";
import type { PageTerm } from "@/lib/craftPageContract";
import { glossaryMeaning, termAliases } from "@/lib/craftPageView";

function TermLabel({ term }: { term: PageTerm }) {
  const reading = useExplainerReading();
  const key = term.key;
  if (!key || reading.hiddenTerms.has(key)) return <span>{term.label}</span>;
  return (
    <button type="button" className={TERM_CLASS} aria-haspopup="dialog" data-testid="term-span" onClick={() => reading.onTerm({ text: term.label, termKey: key })}>
      {term.label}
    </button>
  );
}

function GlossaryEntry({ term }: { term: PageTerm }) {
  const aliases = termAliases(term);
  const meaning = glossaryMeaning(term);
  return (
    <div className="min-w-0 border-t border-line-200 pt-3 first:border-0 first:pt-0" data-testid="craft-term">
      <dt className="text-sm font-semibold text-ink-900 [overflow-wrap:anywhere]">
        <TermLabel term={term} />
        {aliases.length > 0 ? <span className="ml-1.5 text-xs font-normal text-ink-500">{aliases.join(", ")}</span> : null}
      </dt>
      {meaning ? (
        <dd className="mt-1 text-sm leading-6 text-ink-700 [overflow-wrap:anywhere]">
          {meaning}
          <ClaimChips ids={term.claimIds} />
        </dd>
      ) : null}
    </div>
  );
}

export function CraftGlossary({ terms }: { terms: readonly PageTerm[] }) {
  if (terms.length === 0) return null;
  return (
    <section aria-labelledby="craft-glossary-heading" className="panel p-5 md:p-6" data-testid="craft-glossary">
      <h2 id="craft-glossary-heading" className="font-display text-lg font-bold text-ink-900">
        Glossary
      </h2>
      <dl className="mt-4 grid gap-3">
        {terms.map((term) => (
          <GlossaryEntry key={term.key ?? term.label} term={term} />
        ))}
      </dl>
    </section>
  );
}
