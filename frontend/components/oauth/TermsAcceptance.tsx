"use client";

import { Markdown } from "@/components/Markdown";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDate } from "@/lib/format";
import type { TermsOfUse, TermsStatus } from "@/lib/oauthContract";

export function TermsAcceptance({
  status,
  terms,
  ticked,
  disabled,
  onTick
}: {
  status: TermsStatus;
  terms: TermsOfUse | null;
  ticked: boolean;
  disabled: boolean;
  onTick: (ticked: boolean) => void;
}) {
  if (status.acceptedAt) {
    return (
      <section className="grid gap-2 border-t border-rule pt-5" aria-labelledby="terms-h">
        <h2 id="terms-h" className="text-h3 font-reading text-ink-1">MCP terms of use</h2>
        <p className="text-body-sm font-reading text-ink-2">
          You accepted version {status.version} on {formatDate(status.acceptedAt)}.
        </p>
      </section>
    );
  }
  return (
    <section className="grid gap-3 border-t border-rule pt-5" aria-labelledby="terms-h" data-testid="terms-of-use">
      <h2 id="terms-h" className="text-h3 font-reading text-ink-1">MCP terms of use</h2>
      <p className="text-label font-ui text-ink-3">Version {status.version}</p>
      {terms ? (
        <div className="max-w-measure text-body-sm font-reading text-ink-1">
          <Markdown text={terms.body} />
        </div>
      ) : (
        <Skeleton shape="lede" label="Fetching the terms of use" />
      )}
      <label className="flex items-start gap-3 text-body-sm font-reading text-ink-1">
        <input
          type="checkbox"
          className="mt-1.5 h-4 w-4 shrink-0"
          checked={ticked}
          disabled={disabled || !terms}
          onChange={(event) => onTick(event.target.checked)}
        />
        <span>I have read the MCP terms of use, version {status.version}, and accept them.</span>
      </label>
    </section>
  );
}
