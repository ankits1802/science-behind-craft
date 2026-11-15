"use client";

import { CitationChip } from "@/components/answer/CitationChip";
import { EvidenceLevelBadge } from "@/components/answer/EvidenceBadge";
import { uniqueCitations } from "@/lib/citations";
import type { Citation, CraftFacetClaim, SourceRef } from "@/lib/types";

export function NoSourceFound() {
  return <EvidenceLevelBadge level="UNAVAILABLE" />;
}

export function ClaimList({
  claims,
  numbers,
  sourcesById,
  onOpen
}: {
  claims: readonly CraftFacetClaim[];
  numbers: Map<string, number>;
  sourcesById: Map<string, SourceRef>;
  onOpen: (citation: Citation) => void;
}) {
  const shown = claims.filter((claim) => claim.citations.length > 0);
  if (shown.length === 0) return <NoSourceFound />;
  return (
    <ul className="grid gap-2.5">
      {shown.map((claim) => (
        <li key={claim.id} className="text-[15px] leading-7 text-ink-700" data-level={claim.level}>
          {claim.text}
          {uniqueCitations(claim.citations).map((citation) => (
            <CitationChip
              key={`${citation.sourceId}:${citation.claimId}`}
              citation={citation}
              number={numbers.get(citation.sourceId) ?? null}
              title={sourcesById.get(citation.sourceId)?.title ?? null}
              onOpen={onOpen}
            />
          ))}
          {claim.level === "HYPOTHESIS" ? <EvidenceLevelBadge level="HYPOTHESIS" className="ml-1 align-middle" /> : null}
        </li>
      ))}
    </ul>
  );
}
