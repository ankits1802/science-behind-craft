"use client";

import { useOptionalCitations } from "@/components/answer/CitationContext";
import { Cite } from "@/components/editorial/CitationCluster";
import type { SourceCitations } from "@/lib/citations";
import type { Citation, SourceRef } from "@/lib/types";

export const CHIP_SHAPE = "kv-cite inline-flex items-center gap-0.5";
export const QUOTED_CHIP_TONE = "no-underline";

function titledSource(sourceId: string, title: string | null): SourceRef[] {
  if (!title) return [];
  return [{ id: sourceId, kind: "OTHER", title, authors: [], year: null, doi: null, url: null, publisher: null, licence: null, attribution: null, reliability: null }];
}

export function CitationChip({ group, title }: { group: SourceCitations; title: string | null; onOpen?: (citations: readonly Citation[]) => void }) {
  const lookup = useOptionalCitations();
  const numbers = lookup?.numbers ?? new Map(group.number === null ? [] : [[group.sourceId, group.number]]);
  const sourcesById = lookup?.sourcesById ?? new Map(titledSource(group.sourceId, title).map((source) => [source.id, source]));
  return <Cite citations={group.citations} numbers={numbers} sourcesById={sourcesById} />;
}
