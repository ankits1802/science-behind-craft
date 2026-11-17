import { languageCodeShape } from "@/lib/answerLanguages";
import { sourceRefShape, UUID } from "@/lib/answerShapes";
import { quizBlockShape, type QuizBlock } from "@/lib/explainerLearning";
import { list, object, oneOf, type Shape } from "@/lib/shape";
import type { SourceRef } from "@/lib/types";

export type ExplainerQuiz = { schemaVersion: 1; answerId: string; language: string; quiz: QuizBlock; sources: SourceRef[] };

export function answerQuizPath(answerId: string, sectionIds: string[] = []): string {
  const query = new URLSearchParams(sectionIds.map((id) => ["sections", id]));
  const path = `/answers/${encodeURIComponent(answerId)}/quiz`;
  return query.size > 0 ? `${path}?${query.toString()}` : path;
}

export const explainerQuizShape: Shape<ExplainerQuiz> = object<ExplainerQuiz>({
  schemaVersion: oneOf([1] as const),
  answerId: UUID,
  language: languageCodeShape,
  quiz: quizBlockShape,
  sources: list(sourceRefShape)
});
