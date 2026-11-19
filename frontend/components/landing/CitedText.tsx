"use client";

import { useMemo } from "react";

import { Cite } from "@/components/editorial/CitationCluster";
import { sourceNumbers, type LandingSentence } from "@/components/landing/landingContent";
import { cn } from "@/lib/utils";
import type { SourceRef } from "@/lib/types";

export type CiteMaps = { numbers: ReadonlyMap<string, number>; sourcesById: ReadonlyMap<string, SourceRef> };

export function useCiteMaps(sources: readonly SourceRef[]): CiteMaps {
  return useMemo(() => ({ numbers: sourceNumbers(sources), sourcesById: new Map(sources.map((source) => [source.id, source])) }), [sources]);
}

export function CitedText({ sentence, cite, className }: { sentence: LandingSentence; cite: CiteMaps; className?: string }) {
  return (
    <span className={cn("kv-sentence", className)} data-cite-host="">
      {sentence.text}
      {sentence.citations.length > 0 ? <Cite citations={sentence.citations} numbers={cite.numbers} sourcesById={cite.sourcesById} /> : null}
    </span>
  );
}
