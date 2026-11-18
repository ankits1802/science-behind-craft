"use client";

import { Lightbulb, Quote } from "lucide-react";

import { evidenceKindLabel, evidenceLevelLabel } from "@/components/answer/EvidenceBadge";
import type { SourceCitations } from "@/lib/citations";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

export const CHIP_SHAPE =
  "mx-0.5 inline-flex translate-y-[-1px] items-center gap-0.5 rounded-full border px-1.5 align-middle text-[11px] font-semibold leading-[18px] transition pointer-coarse:min-h-7 pointer-coarse:px-2";
export const QUOTED_CHIP_TONE = "border-purple-300 bg-purple-50 text-purple-700 hover:border-purple-500 hover:bg-purple-100 dark:bg-purple-950/40 dark:text-purple-300";

export function CitationChip({ group, title, onOpen }: { group: SourceCitations; title: string | null; onOpen: (citations: readonly Citation[]) => void }) {
  const lead = group.citations.find((citation) => citation.evidence !== "INFERRED") ?? group.citations[0];
  const inferred = lead.evidence === "INFERRED";
  const described = `${evidenceKindLabel(lead.evidence)}, ${evidenceLevelLabel(lead.level)}`;
  return (
    <button
      type="button"
      onClick={() => onOpen(group.citations)}
      title={title ? `${title} · ${described}` : described}
      aria-label={`Source ${group.number ?? ""}, ${described}${title ? `: ${title}` : ""}`}
      aria-haspopup="dialog"
      data-evidence={lead.evidence}
      data-testid="citation-chip"
      className={cn(CHIP_SHAPE, inferred ? "border-amber-500/40 bg-amber-100 text-amber-800 hover:border-amber-500" : QUOTED_CHIP_TONE)}
    >
      {inferred ? <Lightbulb className="h-2.5 w-2.5" aria-hidden /> : <Quote className="h-2.5 w-2.5" aria-hidden />}
      <span className="tabular-nums">{group.number ?? "·"}</span>
      {inferred ? <span>Inferred</span> : null}
    </button>
  );
}
