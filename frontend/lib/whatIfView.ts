import type { WhatIfOption } from "@/lib/explainerPlay";
import { countNoun } from "@/lib/format";

export const UNKNOWN_OUTCOME = "Unknown";

export function isUnknownOption(option: Pick<WhatIfOption, "outcomes">): boolean {
  return option.outcomes.length === 0;
}

export function optionNote(option: Pick<WhatIfOption, "outcomes">): string {
  return isUnknownOption(option) ? UNKNOWN_OUTCOME : countNoun(option.outcomes.length, "cited outcome");
}

export const WHAT_IF_STEP_MS = 4800;

export function whatIfBeat(): number {
  return WHAT_IF_STEP_MS;
}
