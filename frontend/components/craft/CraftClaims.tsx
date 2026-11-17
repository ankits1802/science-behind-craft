"use client";

import { createContext, useContext } from "react";

import { CitationChips } from "@/components/answer/CitationContext";
import { ExplainerSentence } from "@/components/answer/ExplainerSentence";
import type { PageSentence } from "@/lib/craftPageContract";
import { citationsOf, claimsOf, shownSentence, type ClaimIndex } from "@/lib/craftPageView";
import { cn } from "@/lib/utils";

const ClaimsContext = createContext<ClaimIndex | null>(null);

export const CraftClaimsProvider = ClaimsContext.Provider;

export function useCraftClaims(): ClaimIndex {
  const index = useContext(ClaimsContext);
  if (!index) throw new Error("Craft page parts need a CraftClaimsProvider above them.");
  return index;
}

export function usePageClaims(ids: readonly string[]) {
  return claimsOf(useCraftClaims(), ids);
}

export function ClaimChips({ ids, className }: { ids: readonly string[]; className?: string }) {
  const citations = citationsOf(useCraftClaims(), ids);
  return <CitationChips citations={citations} className={className} />;
}

const PROSE = { body: "text-[15px] leading-7 text-ink-700", lede: "text-base leading-8 text-ink-900 md:text-[17px]" } as const;

export function CitedProse({ sentences, tone = "body", className }: { sentences: readonly PageSentence[]; tone?: keyof typeof PROSE; className?: string }) {
  const index = useCraftClaims();
  return (
    <p className={cn(PROSE[tone], className)}>
      {sentences.map((sentence) => (
        <ExplainerSentence key={sentence.id} sentence={shownSentence(index, sentence)} />
      ))}
    </p>
  );
}
