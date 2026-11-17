import { BadgeCheck, Check, Clock, GitCompareArrows, Lightbulb, MinusCircle, Quote, Scale, TriangleAlert, type LucideIcon } from "lucide-react";

import type { EvidenceKind, EvidenceLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

type BadgeMeta = { label: string; Icon: LucideIcon; className: string };

const BADGE = "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold";

const ATTENTION = "border-amber-500/30 bg-amber-100 text-amber-800";

const LEVEL: Record<EvidenceLevel, BadgeMeta> = {
  VERIFIED: {
    label: "Verified",
    Icon: BadgeCheck,
    className: "border-evidence-300 bg-evidence-100 text-evidence-800 dark:border-evidence-800 dark:bg-evidence-950 dark:text-evidence-200"
  },
  REVIEWED: { label: "Reviewed", Icon: Check, className: "border-evidence-300 bg-card text-evidence-700 dark:border-evidence-800 dark:text-evidence-300" },
  PROVISIONAL: { label: "Provisional", Icon: Clock, className: "border-purple-300 bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300" },
  HYPOTHESIS: { label: "Hypothesis", Icon: Lightbulb, className: ATTENTION },
  UNAVAILABLE: { label: "No source found", Icon: MinusCircle, className: "border-line-200 bg-surface-50 text-ink-500" }
};

const KIND: Record<EvidenceKind, BadgeMeta> = {
  QUOTED: { label: "Quoted source", Icon: Quote, className: "border-purple-300 bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300" },
  INFERRED: { label: "Model-inferred", Icon: Lightbulb, className: ATTENTION }
};

export type EvidenceSignal = "SOURCES_DIFFER" | "EXPERTS_DIFFER" | "OUTSIDE_RANGE" | "UNBALANCED" | "BALANCED";

const SIGNAL: Record<EvidenceSignal, BadgeMeta> = {
  SOURCES_DIFFER: { label: "Sources differ", Icon: GitCompareArrows, className: ATTENTION },
  EXPERTS_DIFFER: { label: "Experts differ", Icon: GitCompareArrows, className: ATTENTION },
  OUTSIDE_RANGE: { label: "Outside usual range", Icon: TriangleAlert, className: ATTENTION },
  UNBALANCED: { label: "Unbalanced", Icon: Scale, className: ATTENTION },
  BALANCED: { label: "Balanced", Icon: Scale, className: "border-line-200 bg-card text-ink-700" }
};

export function evidenceLevelLabel(level: EvidenceLevel): string {
  return LEVEL[level]?.label ?? level;
}

export function evidenceKindLabel(kind: EvidenceKind): string {
  return KIND[kind]?.label ?? kind;
}

function MetaBadge({ meta, className }: { meta: BadgeMeta; className?: string }) {
  return (
    <span className={cn(BADGE, meta.className, className)}>
      <meta.Icon className="h-3 w-3" aria-hidden />
      {meta.label}
    </span>
  );
}

export function EvidenceLevelBadge({ level, className }: { level: EvidenceLevel; className?: string }) {
  return <MetaBadge meta={LEVEL[level] ?? LEVEL.UNAVAILABLE} className={className} />;
}

export function EvidenceKindBadge({ kind, className }: { kind: EvidenceKind; className?: string }) {
  return <MetaBadge meta={KIND[kind] ?? KIND.INFERRED} className={className} />;
}

export function EvidenceSignalBadge({ signal, className }: { signal: EvidenceSignal; className?: string }) {
  return <MetaBadge meta={SIGNAL[signal]} className={className} />;
}
