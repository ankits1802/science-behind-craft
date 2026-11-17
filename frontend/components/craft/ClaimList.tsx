"use client";

import { EvidenceLevelBadge } from "@/components/answer/EvidenceBadge";
import { CitationChips } from "@/components/answer/CitationContext";
import type { Citation, EvidenceLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

type ShownClaim = { id: string; text: string; level: EvidenceLevel; citations: readonly Citation[] };

const SIZE = { body: "text-[15px] leading-7", compact: "text-sm leading-6" } as const;

export function NoSourceFound() {
  return <EvidenceLevelBadge level="UNAVAILABLE" />;
}

export function ClaimList({ claims, size = "body" }: { claims: readonly ShownClaim[]; size?: keyof typeof SIZE }) {
  const shown = claims.filter((claim) => claim.citations.length > 0);
  if (shown.length === 0) return <NoSourceFound />;
  return (
    <ul className="grid gap-2.5">
      {shown.map((claim) => (
        <li key={claim.id} className={cn("text-ink-700", SIZE[size])} data-level={claim.level}>
          {claim.text}
          <CitationChips citations={claim.citations} />
          {claim.level === "HYPOTHESIS" ? <EvidenceLevelBadge level="HYPOTHESIS" className="ml-1 align-middle" /> : null}
        </li>
      ))}
    </ul>
  );
}
