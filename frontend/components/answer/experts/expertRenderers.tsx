import type { ComponentType } from "react";

import { ExpertSeatCard } from "@/components/answer/experts/ExpertSeatCard";
import type { ExpertViewBlock } from "@/lib/explainerExperts";

export const EXPERT_RENDERERS: { expert_view: ComponentType<{ block: ExpertViewBlock }> } = {
  expert_view: ExpertSeatCard
};
