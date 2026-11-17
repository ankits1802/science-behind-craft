"use client";

import { ClaimList } from "@/components/craft/ClaimList";
import { usePageClaims } from "@/components/craft/CraftClaims";
import type { PageQuestion } from "@/lib/craftPageContract";

function QuestionItem({ question }: { question: PageQuestion }) {
  const claims = usePageClaims(question.claimIds);
  return (
    <li className="grid min-w-0 gap-2 border-t border-line-200 pt-4 first:border-0 first:pt-0" data-testid="craft-open-question">
      <h3 className="text-[15px] font-semibold leading-6 text-ink-900 [overflow-wrap:anywhere]">{question.question}</h3>
      <ClaimList claims={claims} size="compact" />
      {question.settledBy ? (
        <p className="text-xs leading-5 text-ink-500">
          <span className="font-semibold text-ink-700">Would settle it: </span>
          {question.settledBy}
        </p>
      ) : null}
    </li>
  );
}

export function OpenQuestions({ questions }: { questions: readonly PageQuestion[] }) {
  if (questions.length === 0) return null;
  return (
    <section aria-labelledby="craft-questions-heading" className="panel p-5 md:p-6" data-testid="craft-open-questions">
      <h2 id="craft-questions-heading" className="font-display text-lg font-bold text-ink-900">
        Open questions
      </h2>
      <ul className="mt-4 grid gap-4">
        {questions.map((question) => (
          <QuestionItem key={question.key ?? question.question} question={question} />
        ))}
      </ul>
    </section>
  );
}
