"use client";

import { useCallback, useMemo, useState } from "react";

import type { CitationLookup } from "@/components/answer/CitationContext";
import type { ExplainerReading } from "@/components/answer/ExplainerReading";
import { openedSource, type OpenCitation } from "@/components/answer/SourceDialog";
import { useTermState } from "@/components/answer/useTermState";
import { ENGLISH } from "@/lib/answerLanguages";
import type { CraftPage } from "@/lib/craftPageContract";
import { claimIndex, pageSourceNumbers, pageSourcesById } from "@/lib/craftPageView";
import type { Citation, SourceRef } from "@/lib/types";

export function useCraftReading(page: CraftPage, regionSources: readonly SourceRef[]) {
  const [opened, setOpened] = useState<OpenCitation | null>(null);
  const terms = useTermState();
  const index = useMemo(() => claimIndex(page), [page]);
  const numbers = useMemo(() => pageSourceNumbers(page, regionSources), [page, regionSources]);
  const sourcesById = useMemo(() => pageSourcesById(page, regionSources), [page, regionSources]);
  const onOpen = useCallback(
    (citations: readonly Citation[]) => setOpened(openedSource(citations, numbers, sourcesById)),
    [numbers, sourcesById]
  );
  const lookup = useMemo<CitationLookup>(() => ({ numbers, sourcesById, onOpen }), [numbers, sourcesById, onOpen]);
  const reading = useMemo<ExplainerReading>(
    () => ({ language: ENGLISH, original: false, hiddenTerms: terms.hidden, onTerm: terms.open, listen: null }),
    [terms.hidden, terms.open]
  );
  const closeSource = useCallback(() => setOpened(null), []);
  return { index, numbers, sourcesById, lookup, reading, terms, opened, openSource: setOpened, closeSource };
}
