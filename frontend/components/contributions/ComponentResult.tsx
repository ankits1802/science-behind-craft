"use client";

import { ComponentCard, ExtendActions } from "@/components/contributions/ComponentCard";
import type { ComponentProposal } from "@/components/contributions/useComponentProposal";
import { resultHeadline } from "@/lib/componentProposalContract";
import { fieldTitle, type ProposalForm } from "@/lib/ownProposalsContract";

export function ComponentResult({ proposal, form }: { proposal: ComponentProposal; form: ProposalForm | null }) {
  const result = proposal.result;
  const shown = result?.matches.map((match) => match.component) ?? [];
  return (
    <div className="grid gap-4 empty:hidden" data-testid="component-result">
      <div role="status" aria-live="polite" className="grid gap-2 empty:hidden">
        {result ? (
          <>
            <h2 className="font-reading text-h3 text-ink-1">{resultHeadline(result)}</h2>
            <p className="max-w-measure font-reading text-body-sm text-ink-2">{result.message}</p>
          </>
        ) : null}
      </div>
      {result?.matches.length ? (
        <>
          <p className="max-w-measure font-reading text-body-sm text-ink-2">
            Place one of these by its label in a page&apos;s layout, or extend it: key it to another subject, or propose a variant.
          </p>
          <ul className="grid gap-4">
            {result.matches.map((match) => (
              <ComponentCard key={match.component.label} component={match.component} fieldTitle={fieldTitle(form, match.component.field)} reasons={match.reasons}>
                <ExtendActions disabled={proposal.busy} onExtend={(extension) => proposal.extend(match.component, extension, shown)} />
              </ComponentCard>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}
