"use client";

import { createContext, useContext } from "react";

import type { AnswerLanguage } from "@/lib/answerLanguages";
import type { TermSpan } from "@/lib/explainerContract";
import type { ListenMark } from "@/lib/listen";

export type ExplainerReading = {
  language: AnswerLanguage;
  original: boolean;
  hiddenTerms: ReadonlySet<string>;
  onTerm: (span: TermSpan) => void;
  listen: ListenMark | null;
};

const ReadingContext = createContext<ExplainerReading | null>(null);

export const ExplainerReadingProvider = ReadingContext.Provider;

export function useExplainerReading(): ExplainerReading {
  const reading = useContext(ReadingContext);
  if (!reading) throw new Error("Explainer sentences need an ExplainerReadingProvider above them.");
  return reading;
}
