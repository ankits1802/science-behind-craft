import type { ComponentType } from "react";

import { CompareTable } from "@/components/answer/learning/CompareTable";
import { ConceptGraphBlockView } from "@/components/answer/learning/ConceptGraphView";
import { QuizBlockView } from "@/components/answer/learning/QuizView";
import type { CompareBlock, ConceptGraphBlock, QuizBlock } from "@/lib/explainerLearning";

export const LEARNING_RENDERERS: {
  quiz: ComponentType<{ block: QuizBlock }>;
  compare: ComponentType<{ block: CompareBlock }>;
  concept_graph: ComponentType<{ block: ConceptGraphBlock }>;
} = {
  quiz: QuizBlockView,
  compare: CompareTable,
  concept_graph: ConceptGraphBlockView
};
