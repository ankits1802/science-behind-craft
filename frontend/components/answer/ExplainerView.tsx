"use client";

import { useMemo, useState, type ReactNode } from "react";

import { AnswerIdProvider } from "@/components/answer/AnswerContext";
import { CitationProvider, type CitationLookup } from "@/components/answer/CitationContext";
import { ExplainerBody } from "@/components/answer/ExplainerBody";
import { ExplainerHeader, ORIGINAL_TEXT } from "@/components/answer/ExplainerHeader";
import { ExplainerReadingProvider, type ExplainerReading } from "@/components/answer/ExplainerReading";
import { lazyBlock } from "@/components/answer/lazyBlock";
import { LedeBlock } from "@/components/answer/LedeBlock";
import { ListenDock } from "@/components/answer/ListenDock";
import { openedSource, SourceDialog, type OpenCitation } from "@/components/answer/SourceDialog";
import { TermSheet } from "@/components/answer/TermSheet";
import type { UnderstoodChange } from "@/components/answer/UnderstoodLine";
import { useListen } from "@/components/answer/useListen";
import { useTermState } from "@/components/answer/useTermState";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { languageFor, type AnswerLanguage } from "@/lib/answerLanguages";
import type { Term } from "@/lib/explainerContract";
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
  tools?: ReactNode;
  versions?: ReactNode;
  footer?: ReactNode;
  filmScore?: boolean;
};

const FilmPlayer = lazyBlock(() => import("@/components/answer/film/FilmPlayer").then((module) => module.FilmPlayer), null);

function useCitationLookup(state: ExplainerState, onOpen: (open: OpenCitation) => void): CitationLookup {
  const sourcesById = useMemo(() => new Map(state.sources.map((source) => [source.id, source])), [state.sources]);
  const numbers = useMemo(
    () => explainerSourceNumbers(state.sections, state.openQuestions, state.reactions, state.lede),
    [state.sections, state.openQuestions, state.reactions, state.lede]
  );
  return useMemo(
    () => ({
      numbers,
      sourcesById,
      onOpen: (citations) => onOpen(openedSource(citations, numbers, sourcesById))
    }),
    [numbers, sourcesById, onOpen]
  );
}

export function ExplainerView({ state, streaming, languages, depthLabel, change, listenLanguages, onFollowUp, onFreshResearch, tools, versions, footer, filmScore = false }: ExplainerViewProps) {
  const reduce = useAppReducedMotion();
  const language = languageFor(state.language, languages);
  const [opened, setOpened] = useState<OpenCitation | null>(null);
  const [shown, setShown] = useState("translated");
  const [active, setActive] = useState<string | null>(null);
  const [filming, setFilming] = useState(false);
  const terms = useTermState();
  const listen = useListen(state.answerId, state.language);
  const lookup = useCitationLookup(state, setOpened);
  const translated = hasTranslatedText(state.sections, state.lede);
  const original = translated && shown === ORIGINAL_TEXT;
  const filmable = state.phase === "done" && state.answerId !== null && listenLanguages.includes(state.language);
  const listenable = filmable && listen.status === "idle";
  const refreshable = state.phase === "done" && showsEarlierResearch(state.sections);
  const startFilm = () => {
    listen.stop();
    setFilming(true);
  };
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
            onFilm={filmable ? startFilm : null}
            onFresh={refreshable ? onFreshResearch : null}
            tools={tools}
          />
          {versions}
          {state.lede ? <LedeBlock lede={state.lede} reduce={reduce} /> : null}
          <AnswerIdProvider value={state.phase === "done" ? state.answerId : null}>
            <ExplainerBody state={state} sections={shownSections(state.sections, streaming)} streaming={streaming} reduce={reduce} active={active} onActive={setActive} onFollowUp={onFollowUp} />
          </AnswerIdProvider>
          {footer}
          <SourceDialog open={opened} onClose={() => setOpened(null)} />
          <TermSheet span={terms.span} language={state.language} onClose={terms.close} onMissing={terms.missing} onAsk={ask} onOpenCitation={setOpened} />
          <ListenDock listen={listen} language={language} />
          {filming && state.answerId ? (
            <FilmPlayer answerId={state.answerId} question={state.question} language={language} sections={state.sections} scoreOffered={filmScore} onClose={() => setFilming(false)} />
          ) : null}
        </article>
      </CitationProvider>
    </ExplainerReadingProvider>
  );
}
