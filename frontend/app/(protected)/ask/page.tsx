"use client";

import { Suspense } from "react";
import { RotateCw } from "lucide-react";

import { ExplainerView } from "@/components/answer/ExplainerView";
import { NotEnoughEvidence } from "@/components/answer/NotEnoughEvidence";
import { AskBox } from "@/components/ask/AskBox";
import { AskOptions } from "@/components/ask/AskOptions";
import { useAskScreen } from "@/components/ask/useAskScreen";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { useGsapHeadline } from "@/components/guide/useGsapHeadline";
import { ActionGroup } from "@/components/ui/ActionGroup";

const STARTERS = ["Why does alum fix madder dye on cotton?", "What happens to clay when terracotta is fired?", "How does indigo turn blue on the cloth?"];

export default function AskPage() {
  return (
    <Suspense fallback={null}>
      <AskScreen />
    </Suspense>
  );
}

function AskScreen() {
  const reduce = useAppReducedMotion();
  const headline = useGsapHeadline<HTMLHeadingElement>(reduce);
  const { state, round, config, question, setQuestion, language, dictation, busy, canAsk, options, understood, shownDepth, run, stop, clear } = useAskScreen();
  const started = state.phase !== "idle";

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-6">
      {!started ? (
        <header className="pt-2 md:pt-8">
          <h1 ref={headline} className="display-title text-2xl md:text-center md:text-[2.75rem] md:leading-tight">
            What would you like to understand?
          </h1>
        </header>
      ) : (
        <h1 className="sr-only">Answer</h1>
      )}

      <AskBox
        value={question}
        onChange={setQuestion}
        onSubmit={() => run(question)}
        onStop={stop}
        busy={busy}
        canAsk={canAsk}
        dictation={dictation}
        language={language}
        options={<AskOptions {...options} />}
      />

      {!started ? (
        <ActionGroup>
          {STARTERS.map((starter) => (
            <button key={starter} type="button" className="field-button-secondary" onClick={() => run(starter)}>
              {starter}
            </button>
          ))}
        </ActionGroup>
      ) : null}

      <div className="mx-auto grid w-full max-w-4xl gap-6">
        {state.phase === "failed" ? (
          <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-red-200 bg-error-100 px-4 py-3 text-sm text-error-600">
            <span>{state.error ?? "Couldn't answer that."}</span>
            <button type="button" className="field-button-secondary min-h-9 px-3 py-1.5 text-xs" onClick={() => run(question)}>
              <RotateCw className="h-3.5 w-3.5" aria-hidden />
              Try again
            </button>
          </div>
        ) : null}

        {started ? (
          <ExplainerView
            key={round}
            state={state}
            streaming={busy}
            languages={config.languages}
            depthLabel={shownDepth}
            change={understood}
            listenLanguages={config.listenLanguages}
            onFollowUp={(next) => {
              clear();
              run(next, { languageChoice: state.language });
            }}
            onFreshResearch={() => run(state.question, { languageChoice: state.language, fresh: true })}
          />
        ) : null}

        {state.phase === "empty" && state.notice ? <NotEnoughEvidence message={state.notice} /> : null}
      </div>
    </div>
  );
}
