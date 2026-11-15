import { BadgeCheck, Check, Clock, Lightbulb, MinusCircle, Quote, type LucideIcon } from "lucide-react";

import type { EvidenceKind, EvidenceLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

const LEVEL: Record<EvidenceLevel, { label: string; Icon: LucideIcon; className: string }> = {
  VERIFIED: { label: "Verified", Icon: BadgeCheck, className: "border-success-600/25 bg-success-100 text-success-600" },
  REVIEWED: { label: "Reviewed", Icon: Check, className: "border-success-600/25 bg-card text-success-600 dark:text-emerald-400" },
  PROVISIONAL: { label: "Provisional", Icon: Clock, className: "border-purple-300 bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300" },
  HYPOTHESIS: { label: "Hypothesis", Icon: Lightbulb, className: "border-amber-500/30 bg-amber-100 text-amber-800" },
  UNAVAILABLE: { label: "No source found", Icon: MinusCircle, className: "border-line-200 bg-surface-50 text-ink-500" }
};

const KIND: Record<EvidenceKind, { label: string; Icon: LucideIcon; className: string }> = {
  QUOTED: { label: "Quoted source", Icon: Quote, className: "border-purple-300 bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300" },
  INFERRED: { label: "Model-inferred", Icon: Lightbulb, className: "border-amber-500/30 bg-amber-100 text-amber-800" }
};

export function evidenceLevelLabel(level: EvidenceLevel): string {
  return LEVEL[level]?.label ?? level;
}

export function evidenceKindLabel(kind: EvidenceKind): string {
  return KIND[kind]?.label ?? kind;
}

export function EvidenceLevelBadge({ level, className }: { level: EvidenceLevel; className?: string }) {
  const meta = LEVEL[level] ?? LEVEL.UNAVAILABLE;
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold", meta.className, className)}>
      <meta.Icon className="h-3 w-3" aria-hidden />
      {meta.label}
    </span>
  );
}

export function EvidenceKindBadge({ kind, className }: { kind: EvidenceKind; className?: string }) {
  const meta = KIND[kind] ?? KIND.INFERRED;
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold", meta.className, className)}>
      <meta.Icon className="h-3 w-3" aria-hidden />
      {meta.label}
    </span>
  );
}
