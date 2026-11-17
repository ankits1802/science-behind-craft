import { QUIZ_BLANK, type QuizOption, type QuizQuestion } from "@/lib/explainerLearning";

export type QuizPick = number | null;
export type OptionMark = "open" | "right" | "wrong" | "other";
export type QuizScore = { right: number; answered: number; total: number };

function folded(option: QuizOption): string {
  return option.text.toLocaleLowerCase("en");
}

export function optionOrder(options: readonly QuizOption[]): number[] {
  const order = options.map((_, index) => index);
  return order.sort((a, b) => {
    const left = folded(options[a]);
    const right = folded(options[b]);
    if (left === right) return a - b;
    return left < right ? -1 : 1;
  });
}

export function promptParts(prompt: string): [string, string] | null {
  const at = prompt.indexOf(QUIZ_BLANK);
  return at < 0 ? null : [prompt.slice(0, at), prompt.slice(at + QUIZ_BLANK.length)];
}

export function optionMark(question: QuizQuestion, picked: QuizPick, index: number): OptionMark {
  if (picked === null) return "open";
  if (index === question.answer) return "right";
  return index === picked ? "wrong" : "other";
}

export function quizScore(questions: readonly QuizQuestion[], picks: readonly QuizPick[]): QuizScore {
  const answered = questions.filter((_, index) => (picks[index] ?? null) !== null).length;
  const right = questions.filter((question, index) => picks[index] === question.answer).length;
  return { right, answered, total: questions.length };
}

export function scoreText(score: QuizScore): string {
  if (score.answered === 0) return score.total === 1 ? "1 question" : `${score.total} questions`;
  const shown = `${score.right} of ${score.answered} right`;
  return score.answered < score.total ? `${shown} · ${score.total - score.answered} to go` : shown;
}

export function picked(picks: readonly QuizPick[], index: number, choice: number): QuizPick[] {
  if ((picks[index] ?? null) !== null) return [...picks];
  const next = [...picks];
  next[index] = choice;
  return next;
}
