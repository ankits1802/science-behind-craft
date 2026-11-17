"use client";

import { useState } from "react";
import { RotateCcw } from "lucide-react";

import { QuizQuestionCard } from "@/components/answer/learning/QuizQuestionCard";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import type { QuizBlock } from "@/lib/explainerLearning";
import { picked, quizScore, scoreText, type QuizPick } from "@/lib/quizView";

function unanswered(block: QuizBlock): QuizPick[] {
  return block.questions.map(() => null);
}

export function QuizView({ block, reduce, initialPicks }: { block: QuizBlock; reduce: boolean; initialPicks?: readonly QuizPick[] }) {
  const [picks, setPicks] = useState<QuizPick[]>(() => (initialPicks ? [...initialPicks] : unanswered(block)));
  const score = quizScore(block.questions, picks);
  const total = block.questions.length;
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3" data-testid="quiz">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <p className="text-sm font-semibold tabular-nums text-ink-700" aria-live="polite" data-testid="quiz-score">
          {scoreText(score)}
        </p>
        {score.answered === total ? (
          <button type="button" className="field-button-secondary min-h-10 rounded-full" onClick={() => setPicks(unanswered(block))} data-testid="quiz-again">
            <RotateCcw className="h-4 w-4" aria-hidden />
            Start again
          </button>
        ) : null}
      </div>
      <ol className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3">
        {block.questions.map((question, index) => (
          <QuizQuestionCard
            key={question.prompt}
            question={question}
            id={`${block.id}-q${index + 1}`}
            position={`Question ${index + 1} of ${total}`}
            pick={picks[index] ?? null}
            reduce={reduce}
            onPick={(choice) => setPicks((current) => picked(current, index, choice))}
          />
        ))}
      </ol>
    </div>
  );
}

export function QuizBlockView({ block }: { block: QuizBlock }) {
  const reduce = useAppReducedMotion();
  return <QuizView block={block} reduce={reduce} />;
}
