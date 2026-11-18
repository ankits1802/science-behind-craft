"use client";

import { Suspense } from "react";
import { RotateCw } from "lucide-react";

import { ExplainerView } from "@/components/answer/ExplainerView";
import { NotEnoughEvidence } from "@/components/answer/NotEnoughEvidence";
import { AskBox } from "@/components/ask/AskBox";
import { AskOptions } from "@/components/ask/AskOptions";
import { useAskScreen } from "@/components/ask/useAskScreen";
import { useExplainerLearning } from "@/components/ask/useExplainerLearning";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { failureMessage } from "@/components/hooks/useRemote";
import { ExplainerNext } from "@/components/learn/ExplainerFooter";
import { ExplainerTools, VersionPicker } from "@/components/learn/ExplainerTools";
import { LoadingPanel, RetryPanel } from "@/components/RemotePanels";
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
  const { state, round, config, question, setQuestion, language, dictation, busy, canAsk, options, understood, shownDepth, run, follow, load, stop, clear } = useAskScreen();
  const learning = useExplainerLearning({ state, load, follow, setQuestion });
  const started = state.phase !== "idle";
  const onFollowUp = (next: string) => {
    if (learning.canFollow) return learning.askFollowUp(next);
    clear();
    run(next, { languageChoice: state.language });
  };

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-6">
      {!started && !learning.opening ? (
        <header className="pt-2 md:pt-8">
          <h1 className="display-title text-2xl md:text-center md:text-[2.75rem] md:leading-tight">
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

      {!started && !learning.opening ? (
        <ActionGroup>
          {STARTERS.map((starter) => (
            <button key={starter} type="button" className="field-button-secondary" onClick={() => run(starter)}>
              {starter}
            </button>
          ))}
        </ActionGroup>
      ) : null}

      <div className="mx-auto grid w-full min-w-0 max-w-4xl gap-6">
        {learning.failure ? <RetryPanel message={failureMessage({ cause: learning.failure }, "Couldn't open that explainer.")} onRetry={learning.retry} /> : null}
        {learning.opening && !learning.failure ? <LoadingPanel /> : null}

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
            filmScore={config.filmScore}
            onFollowUp={onFollowUp}
            onFreshResearch={() => run(state.question, { languageChoice: state.language, fresh: true })}
            tools={learning.ref ? <ExplainerTools explainer={learning.ref} /> : null}
            versions={learning.ref ? <VersionPicker choice={{ versions: learning.versions, viewing: state.mark, onPick: learning.pickVersion }} sections={state.sections} /> : null}
            footer={learning.ref ? <ExplainerNext state={state} canFollow={learning.canFollow} onFollowUp={learning.askFollowUp} reduce={reduce} /> : null}
          />
        ) : null}

        {state.phase === "empty" && state.notice ? <NotEnoughEvidence message={state.notice} /> : null}
      </div>
    </div>
  );
}
