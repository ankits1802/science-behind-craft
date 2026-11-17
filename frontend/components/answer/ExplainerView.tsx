"use client";

import { useCallback, useMemo, useState } from "react";

import { CitationProvider, type CitationLookup } from "@/components/answer/CitationContext";
import { ExplainerBody } from "@/components/answer/ExplainerBody";
import { ExplainerHeader, ORIGINAL_TEXT } from "@/components/answer/ExplainerHeader";
import { ExplainerReadingProvider, type ExplainerReading } from "@/components/answer/ExplainerReading";
import { ListenDock } from "@/components/answer/ListenDock";
import { SourceDialog, type OpenCitation } from "@/components/answer/SourceDialog";
import { TermSheet } from "@/components/answer/TermSheet";
import type { UnderstoodChange } from "@/components/answer/UnderstoodLine";
import { useListen } from "@/components/answer/useListen";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { languageFor, type AnswerLanguage } from "@/lib/answerLanguages";
import type { Term, TermSpan } from "@/lib/explainerContract";
import type { ExplainerState } from "@/lib/explainerState";
import { explainerSourceNumbers, hasTranslatedText, shownSections, showsEarlierResearch, termQuestion } from "@/lib/explainerView";

export type ExplainerViewProps = {
  state: ExplainerState;
  streaming: boolean;
  languages: AnswerLanguage[];
  depthLabel: string | null;
  change: UnderstoodChange;
  listenLanguages: readonly string[];
  onFollowUp: ((question: string) => void) | null;
  onFreshResearch: (() => void) | null;
};

function useCitationLookup(state: ExplainerState, onOpen: (open: OpenCitation) => void): CitationLookup {
  const sourcesById = useMemo(() => new Map(state.sources.map((source) => [source.id, source])), [state.sources]);
  const numbers = useMemo(() => explainerSourceNumbers(state.sections, state.openQuestions, state.reactions), [state.sections, state.openQuestions, state.reactions]);
  return useMemo(
    () => ({
      numbers,
      sourcesById,
      onOpen: (citation) => onOpen({ citation, source: sourcesById.get(citation.sourceId) ?? null, number: numbers.get(citation.sourceId) ?? null })
    }),
    [numbers, sourcesById, onOpen]
  );
}

function useTermState() {
  const [span, setSpan] = useState<TermSpan | null>(null);
  const [hidden, setHidden] = useState<ReadonlySet<string>>(() => new Set());
  const close = useCallback(() => setSpan(null), []);
  const missing = useCallback((key: string) => {
    setHidden((current) => new Set([...current, key]));
    setSpan(null);
  }, []);
  return { span, hidden, open: setSpan, close, missing };
}

export function ExplainerView({ state, streaming, languages, depthLabel, change, listenLanguages, onFollowUp, onFreshResearch }: ExplainerViewProps) {
  const reduce = useAppReducedMotion();
  const language = languageFor(state.language, languages);
  const [opened, setOpened] = useState<OpenCitation | null>(null);
  const [shown, setShown] = useState("translated");
  const [active, setActive] = useState<string | null>(null);
  const terms = useTermState();
  const listen = useListen(state.answerId, state.language);
  const lookup = useCitationLookup(state, setOpened);
  const translated = hasTranslatedText(state.sections);
  const original = translated && shown === ORIGINAL_TEXT;
  const listenable = state.phase === "done" && state.answerId !== null && listenLanguages.includes(state.language) && listen.status === "idle";
  const refreshable = state.phase === "done" && showsEarlierResearch(state.sections);
  const reading = useMemo<ExplainerReading>(
    () => ({ language, original, hiddenTerms: terms.hidden, onTerm: terms.open, listen: listen.mark }),
    [language, original, terms.hidden, terms.open, listen.mark]
  );
  const craftName = state.understood?.crafts[0]?.name ?? null;
  const ask = onFollowUp ? (term: Term) => onFollowUp(termQuestion(term.label, craftName)) : null;

  return (
    <ExplainerReadingProvider value={reading}>
      <CitationProvider value={lookup}>
        <article className="grid gap-5" aria-busy={streaming || undefined} data-testid="answer-view">
          <ExplainerHeader
            understood={state.understood}
            depthLabel={depthLabel}
            language={language}
            change={change}
            shown={{ translated, original, onShow: setShown }}
            onListen={listenable ? listen.start : null}
            onFresh={refreshable ? onFreshResearch : null}
          />
          <ExplainerBody state={state} sections={shownSections(state.sections, streaming)} streaming={streaming} reduce={reduce} active={active} onActive={setActive} onFollowUp={onFollowUp} />
          <SourceDialog open={opened} onClose={() => setOpened(null)} />
          <TermSheet span={terms.span} language={state.language} onClose={terms.close} onMissing={terms.missing} onAsk={ask} onOpenCitation={setOpened} />
          <ListenDock listen={listen} language={language} />
        </article>
      </CitationProvider>
    </ExplainerReadingProvider>
  );
}
