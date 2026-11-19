"use client";

import { formatDate } from "@/lib/format";
import { CONTRIBUTION_TERMS_POINTS, type TermsStatus } from "@/lib/ownProposalsContract";

export function TermsConsent({
  terms,
  ticked,
  disabled,
  onTick
}: {
  terms: TermsStatus;
  ticked: boolean;
  disabled: boolean;
  onTick: (ticked: boolean) => void;
}) {
  if (terms.acceptedAt) {
    return (
      <p className="font-ui text-label text-ink-2" data-testid="terms-accepted">
        You accepted the contribution terms, version {terms.version}, on {formatDate(terms.acceptedAt)}.
      </p>
    );
  }
  return (
    <fieldset className="grid gap-3 border-t border-rule pt-5" data-testid="contribution-terms">
      <legend className="font-headline text-h3 text-ink-1">Contribution terms</legend>
      <p className="kicker">Version {terms.version}</p>
      <ul className="grid max-w-measure list-disc gap-2 ps-5 font-reading text-body-sm text-ink-1">
        {CONTRIBUTION_TERMS_POINTS.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
      <label className="flex items-start gap-3 font-reading text-body-sm text-ink-1">
        <input
          type="checkbox"
          className="mt-1.5 h-4 w-4 shrink-0"
          checked={ticked}
          disabled={disabled}
          onChange={(event) => onTick(event.target.checked)}
        />
        <span>I have read the contribution terms, version {terms.version}, and accept them.</span>
      </label>
    </fieldset>
  );
}
