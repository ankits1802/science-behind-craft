"use client";

import { useMemo, useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowRight, GitCompareArrows, MessageCirclePlus } from "lucide-react";

import { QuizView } from "@/components/answer/learning/QuizView";
import { useRemote } from "@/components/hooks/useRemote";
import { Accordion } from "@/components/ui/Accordion";
import { askable, QUESTION_MAX } from "@/lib/askRequest";
import { compareSuggestions } from "@/lib/comparePage";
import type { Understood } from "@/lib/explainerContract";
import type { ExplainerState } from "@/lib/explainerState";
import { countNoun } from "@/lib/format";
import { fetchExplainerQuiz } from "@/lib/learningApi";

export function FollowUpBox({ onAsk }: { onAsk: (question: string) => void }) {
  const [question, setQuestion] = useState("");
  const ready = askable(question);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ready) return;
    onAsk(question.trim());
    setQuestion("");
  }
  return (
    <form onSubmit={submit} className="panel grid min-w-0 gap-3 p-4 md:p-5" data-testid="follow-up">
      <label htmlFor="follow-up-question" className="flex items-center gap-2 font-display text-base font-bold text-ink-900">
        <MessageCirclePlus className="h-4 w-4 text-purple-700 dark:text-purple-300" aria-hidden />
        Ask a follow-up
      </label>
      <textarea
        id="follow-up-question"
        rows={2}
        maxLength={QUESTION_MAX}
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder="What else would you like to know?"
        className="field-input min-h-20 resize-y"
      />
      <button type="submit" className="field-button w-full sm:w-fit sm:justify-self-end" disabled={!ready}>
        Add to this explainer
        <ArrowRight className="h-4 w-4" aria-hidden />
      </button>
    </form>
  );
}

export function CompareLinks({ understood }: { understood: Understood }) {
  const links = compareSuggestions(understood.crafts, understood.candidates);
  if (links.length === 0) return null;
  return (
    <nav aria-label="Compare" className="flex min-w-0 flex-wrap gap-2" data-testid="compare-links">
      {links.map((link) => (
        <Link key={link.href} href={link.href} className="field-button-secondary min-h-10 max-w-full rounded-full px-4">
          <GitCompareArrows className="h-4 w-4 shrink-0" aria-hidden />
          <span className="min-w-0 truncate">{link.label}</span>
        </Link>
      ))}
    </nav>
  );
}

export function SelfCheck({ answerId, reduce }: { answerId: string; reduce: boolean }) {
  const load = useMemo(() => () => fetchExplainerQuiz(answerId), [answerId]);
  const quiz = useRemote(load);
  if (!quiz.data) return null;
  return (
    <div data-testid="self-check">
      <Accordion title="Check yourself" subtitle={countNoun(quiz.data.quiz.questions.length, "question")}>
        <QuizView block={quiz.data.quiz} reduce={reduce} />
      </Accordion>
    </div>
  );
}

export function ExplainerNext({ state, canFollow, onFollowUp, reduce }: { state: ExplainerState; canFollow: boolean; onFollowUp: (question: string) => void; reduce: boolean }) {
  return (
    <div className="grid min-w-0 gap-4" data-testid="explainer-next">
      {state.understood ? <CompareLinks understood={state.understood} /> : null}
      {state.phase === "done" && state.answerId ? <SelfCheck answerId={state.answerId} reduce={reduce} /> : null}
      {canFollow ? <FollowUpBox onAsk={onFollowUp} /> : null}
    </div>
  );
}
