"use client";

import { ExternalLink } from "lucide-react";

import { EvidenceKindBadge, EvidenceLevelBadge } from "@/components/answer/EvidenceBadge";
import { FieldDialog } from "@/components/dialogs/FieldDialog";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { highlightQuote, sourceByline, sourceHost, sourceHref } from "@/lib/citations";
import type { Citation, SourceRef } from "@/lib/types";

export type OpenCitation = { citation: Citation; source: SourceRef | null; number: number | null };

export function SourceDialog({ open, onClose }: { open: OpenCitation | null; onClose: () => void }) {
  const source = open?.source ?? null;
  const citation = open?.citation ?? null;
  const href = source ? sourceHref(source) : null;
  const host = sourceHost(href);
  const parts = citation ? highlightQuote(citation.context, citation.quote) : [];

  return (
    <FieldDialog
      open={open !== null}
      onClose={onClose}
      title={source?.title ?? "Source"}
      description={source ? sourceByline(source) || undefined : undefined}
      className="max-w-xl"
      footer={
        <ActionGroup align="end">
          {href ? (
            <a href={href} target="_blank" rel="noopener noreferrer" className="field-button" data-testid="source-outbound">
              Read at {host ?? "source"}
              <ExternalLink className="h-4 w-4" aria-hidden />
            </a>
          ) : null}
          <button type="button" className="field-button-secondary" onClick={onClose}>
            Close
          </button>
        </ActionGroup>
      }
    >
      {citation ? (
        <div className="grid gap-4">
          <div className="flex flex-wrap items-center gap-1.5">
            {open?.number ? <span className="font-display text-sm font-bold tabular-nums text-purple-700 dark:text-purple-300">[{open.number}]</span> : null}
            <EvidenceKindBadge kind={citation.evidence} />
            <EvidenceLevelBadge level={citation.level} />
          </div>
          {parts.length > 0 ? (
            <blockquote className="rounded-md border-l-4 border-purple-300 bg-surface-50 px-4 py-3 text-sm leading-7 text-ink-700" data-testid="source-passage">
              {parts.map((part, index) =>
                part.mark ? (
                  <mark key={index} className="rounded-sm bg-purple-100 px-0.5 font-medium text-ink-900 dark:bg-purple-800/60 dark:text-white">
                    {part.text}
                  </mark>
                ) : (
                  <span key={index}>{part.text}</span>
                )
              )}
            </blockquote>
          ) : (
            <p className="text-sm text-ink-500">Inferred from the cited source; no passage is quoted.</p>
          )}
          <dl className="grid grid-cols-[7rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-xs">
            {citation.locator ? (
              <>
                <dt className="text-ink-500">Location</dt>
                <dd className="text-ink-900">{citation.locator}</dd>
              </>
            ) : null}
            {source?.licence ? (
              <>
                <dt className="text-ink-500">Licence</dt>
                <dd className="text-ink-900">{source.licence}</dd>
              </>
            ) : null}
            {source?.attribution ? (
              <>
                <dt className="text-ink-500">Attribution</dt>
                <dd className="text-ink-900">{source.attribution}</dd>
              </>
            ) : null}
            {source?.doi ? (
              <>
                <dt className="text-ink-500">DOI</dt>
                <dd className="break-all text-ink-900">{source.doi}</dd>
              </>
            ) : null}
          </dl>
        </div>
      ) : null}
    </FieldDialog>
  );
}
