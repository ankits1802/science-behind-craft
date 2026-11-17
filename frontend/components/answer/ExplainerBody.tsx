"use client";

import { AnswerProgress } from "@/components/answer/AnswerProgress";
import { SectionBlock } from "@/components/answer/AnswerSectionBlock";
import { ExplainerSectionView } from "@/components/answer/ExplainerSectionView";
import { ReactionsPanel } from "@/components/answer/ReactionsPanel";
import { SectionBar } from "@/components/answer/SectionBar";
import { SourcesList, type NumberedSource } from "@/components/answer/SourcesList";
import { useCitations } from "@/components/answer/CitationContext";
import { useExplainerReading } from "@/components/answer/ExplainerReading";
import { ResearchTrail } from "@/components/answer/ResearchTrail";
import { Accordion } from "@/components/ui/Accordion";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { attributesForText } from "@/lib/answerLanguages";
import type { ExplainerState, SectionView } from "@/lib/explainerState";

export type BodyProps = {
  state: ExplainerState;
  sections: SectionView[];
  streaming: boolean;
  reduce: boolean;
  active: string | null;
  onActive: (id: string) => void;
  onFollowUp: ((question: string) => void) | null;
};

function numberedSources(numbers: Map<string, number>, sourcesById: Map<string, ExplainerState["sources"][number]>): NumberedSource[] {
  return [...numbers.entries()].sort((a, b) => a[1] - b[1]).map(([id, number]) => ({ number, id, source: sourcesById.get(id) ?? null }));
}

function OpenQuestions({ state, reduce }: { state: ExplainerState; reduce: boolean }) {
  const { language, original } = useExplainerReading();
  const { numbers, sourcesById, onOpen } = useCitations();
  if (!state.openQuestions.some((section) => section.sentences.length > 0)) return null;
  return (
    <Accordion title="Open questions" subtitle="Hypotheses with no direct quote.">
      <div className="grid gap-4">
        {state.openQuestions.map((section) => (
          <SectionBlock key={section.id} section={section} reduce={reduce} numbers={numbers} sourcesById={sourcesById} onOpen={onOpen} compact language={language} original={original} />
        ))}
      </div>
    </Accordion>
  );
}

function FollowUps({ items, onFollowUp }: { items: string[]; onFollowUp: (question: string) => void }) {
  const { language } = useExplainerReading();
  return (
    <section aria-label="Ask next">
      <h2 className="field-label mb-2">Ask next</h2>
      <ActionGroup align="start">
        {items.map((question) => (
          <button key={question} type="button" className="field-button-secondary" onClick={() => onFollowUp(question)} {...attributesForText(question, language)}>
            {question}
          </button>
        ))}
      </ActionGroup>
    </section>
  );
}

export function ExplainerBody({ state, sections, streaming, reduce, active, onActive, onFollowUp }: BodyProps) {
  const { numbers, sourcesById, onOpen } = useCitations();
  const numbered = numberedSources(numbers, sourcesById);
  const writing = sections.some((section) => section.blocks.length > 0);
  return (
    <>
      <ResearchTrail trail={state.trail} live={streaming} reduce={reduce} />
      <SectionBar sections={sections} active={active} streaming={streaming} reduce={reduce} onPick={onActive} />
      {streaming ? <AnswerProgress status={state.status} writing={writing} /> : null}
      {sections.map((section) => (
        <ExplainerSectionView key={section.id} section={section} streaming={streaming} reduce={reduce} onActive={onActive} />
      ))}
      {state.reactions.length > 0 ? <ReactionsPanel reactions={state.reactions} numbers={numbers} sourcesById={sourcesById} onOpen={onOpen} /> : null}
      <OpenQuestions state={state} reduce={reduce} />
      {numbered.length > 0 ? <SourcesList entries={numbered} /> : null}
      {!streaming && state.followUps.length > 0 && onFollowUp ? <FollowUps items={state.followUps} onFollowUp={onFollowUp} /> : null}
    </>
  );
}
