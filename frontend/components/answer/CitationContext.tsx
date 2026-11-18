"use client";

import { createContext, useContext } from "react";

import { CitationChip } from "@/components/answer/CitationChip";
import { citationsBySource } from "@/lib/citations";
import type { Citation, SourceRef } from "@/lib/types";
import { cn } from "@/lib/utils";

export type CitationLookup = {
  numbers: Map<string, number>;
  sourcesById: Map<string, SourceRef>;
  onOpen: (citations: readonly Citation[]) => void;
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
  const groups = citationsBySource(citations, numbers);
  if (groups.length === 0) return null;
  return (
    <span className={cn("inline", className)}>
      {groups.map((group) => (
        <CitationChip key={group.sourceId} group={group} title={sourcesById.get(group.sourceId)?.title ?? null} onOpen={onOpen} />
      ))}
    </span>
  );
}
