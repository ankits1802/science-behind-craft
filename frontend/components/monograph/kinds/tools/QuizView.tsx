"use client";

import { useMemo, useState, type ReactNode } from "react";

import { LegacyScope } from "@/components/monograph/LegacyScope";
import { useMonographSlot } from "@/components/monograph/MonographSlotContext";
import { parseToolSpec, quizSpecShape, type QuizQuestion } from "@/lib/componentSpecsTools";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { nodeElements } from "@/lib/monographRenderElements";

export const BLANK = "\u2002\u2002\u2002\u2002";

export function quizCount(at: number, total: number): string {
  return `Question ${at + 1} of ${total}`;
}

export function quizVerdict(question: QuizQuestion, picked: string): string {
  const right = question.choices.find((choice) => choice.right)?.term ?? "";
  return picked === right ? `Right: ${right}.` : `Not quite: the word is ${right}.`;
}

export function quizScore(results: readonly boolean[], total: number): string {
  return `${results.filter(Boolean).length} of ${total}`;
}

type Answer = { at: number; picked: string | null; results: boolean[] };

function stepClass(answer: Answer, at: number): string | undefined {
  if (answer.results[at] === true) return "done-right";
  if (answer.results[at] === false) return "done-wrong";
  return at === answer.at ? "on" : undefined;
}

function QuestionView({ question, picked, onPick }: { question: QuizQuestion; picked: string | null; onPick: (term: string) => void }) {
  const { sources } = useMonographSlot();
  return (
    <>
      <p className="quiz-q">
        {question.before}{" "}
        <span className="quiz-blank">
          {picked ?? (
            <>
              <span aria-hidden="true">{BLANK}</span>
              <span className="sr-only">blank</span>
            </>
          )}
        </span>{" "}
        {question.after}
        {nodeElements([{ m: "cite", key: question.cite.key, g: question.cite.sources, c: [] }], sources)}
      </p>
      <div className="quiz-opts" role="group" aria-label="Choices">
        {question.choices.map((choice) => (
          <div key={choice.term} className="quiz-opt-row">
            <button type="button" className="quiz-opt" aria-pressed={picked === choice.term} disabled={picked !== null} onClick={() => onPick(choice.term)}>
              <i>{choice.term}</i>
            </button>
            {picked ? <p className="quiz-src">{nodeElements(choice.sentence, sources)}</p> : null}
          </div>
        ))}
      </div>
    </>
  );
}

function useQuiz(questions: readonly QuizQuestion[]) {
  const [answer, setAnswer] = useState<Answer>({ at: 0, picked: null, results: [] });
  const question = answer.at < questions.length ? questions[answer.at] : null;
  const pick = (term: string) => {
    if (!question || answer.picked) return;
    const right = question.choices.some((choice) => choice.right && choice.term === term);
    setAnswer({ ...answer, picked: term, results: [...answer.results, right] });
  };
  const next = () => setAnswer({ ...answer, at: answer.at + 1, picked: null });
  return { answer, question, pick, next };
}

export function QuizView({ spec, renderUnit }: ComponentViewProps) {
  const quiz = useMemo(() => parseToolSpec(quizSpecShape, spec), [spec]);
  const { answer, question, pick, next } = useQuiz(quiz.questions);
  const total = quiz.questions.length;
  return (
    <LegacyScope scope="rm">
      <div className="end-block">
        <div className="end-h">
          <h3>{renderUnit(quiz.title)}</h3>
          <span className="kicker">{quiz.kicker}</span>
        </div>
        <p className="end-dek">{renderUnit(quiz.dek)}</p>
        <div className="quiz">
          <div className="quiz-top">
            <p className="quiz-steps" aria-hidden="true">
              {quiz.questions.map((_, at) => (
                <i key={at} className={stepClass(answer, at)} />
              ))}
            </p>
            {question ? <span className="quiz-count">{quizCount(answer.at, total)}</span> : null}
          </div>
          {question ? (
            <QuestionView question={question} picked={answer.picked} onPick={pick} />
          ) : (
            <div className="quiz-done">
              <p className="score">{quizScore(answer.results, total)}</p>
            </div>
          )}
          {question ? <QuizFoot status={answer.picked ? quizVerdict(question, answer.picked) : renderUnit(quiz.status)} next={quiz.nextLabel} ready={answer.picked !== null} onNext={next} /> : null}
        </div>
      </div>
    </LegacyScope>
  );
}

function QuizFoot({ status, next, ready, onNext }: { status: ReactNode; next: string; ready: boolean; onNext: () => void }) {
  return (
    <div className="quiz-foot">
      <p className="quiz-status" role="status">
        {status}
      </p>
      <div className="actions" data-count="1">
        <button className="btn sm" type="button" disabled={!ready} onClick={onNext}>
          {next}
        </button>
      </div>
    </div>
  );
}
