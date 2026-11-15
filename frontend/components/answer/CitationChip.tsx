"use client";

import { Lightbulb, Quote } from "lucide-react";

import { evidenceKindLabel } from "@/components/answer/EvidenceBadge";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

export function CitationChip({ citation, number, title, onOpen }: { citation: Citation; number: number | null; title: string | null; onOpen: (citation: Citation) => void }) {
  const inferred = citation.evidence === "INFERRED";
  const kind = evidenceKindLabel(citation.evidence);
  return (
    <button
      type="button"
      onClick={() => onOpen(citation)}
      title={title ? `${title} · ${kind}` : kind}
      aria-label={`Source ${number ?? ""}, ${kind}${title ? `: ${title}` : ""}`}
      data-evidence={citation.evidence}
      data-testid="citation-chip"
      className={cn(
        "mx-0.5 inline-flex translate-y-[-1px] items-center gap-0.5 rounded-full border px-1.5 align-middle text-[11px] font-semibold leading-[18px] transition pointer-coarse:min-h-7 pointer-coarse:px-2",
        inferred
          ? "border-amber-500/40 bg-amber-100 text-amber-800 hover:border-amber-500"
          : "border-purple-300 bg-purple-50 text-purple-700 hover:border-purple-500 hover:bg-purple-100 dark:bg-purple-950/40 dark:text-purple-300"
      )}
    >
      {inferred ? <Lightbulb className="h-2.5 w-2.5" aria-hidden /> : <Quote className="h-2.5 w-2.5" aria-hidden />}
      <span className="tabular-nums">{number ?? "·"}</span>
      {inferred ? <span>Inferred</span> : null}
    </button>
  );
}
