"use client";

import { createContext, useContext } from "react";

import { CitationChip } from "@/components/answer/CitationChip";
import { uniqueCitations } from "@/lib/citations";
import type { Citation, SourceRef } from "@/lib/types";
import { cn } from "@/lib/utils";

export type CitationLookup = {
  numbers: Map<string, number>;
  sourcesById: Map<string, SourceRef>;
  onOpen: (citation: Citation) => void;
};

const CitationContext = createContext<CitationLookup | null>(null);

export const CitationProvider = CitationContext.Provider;

export function useCitations(): CitationLookup {
  const lookup = useContext(CitationContext);
  if (!lookup) throw new Error("Citation chips need a CitationProvider above them.");
  return lookup;
}

export function CitationChips({ citations, className }: { citations: readonly Citation[]; className?: string }) {
  const { numbers, sourcesById, onOpen } = useCitations();
  const shown = uniqueCitations(citations);
  if (shown.length === 0) return null;
  return (
    <span className={cn("inline", className)}>
      {shown.map((citation) => (
        <CitationChip
          key={`${citation.sourceId}:${citation.claimId}`}
          citation={citation}
          number={numbers.get(citation.sourceId) ?? null}
          title={sourcesById.get(citation.sourceId)?.title ?? null}
          onOpen={onOpen}
        />
      ))}
    </span>
  );
}
