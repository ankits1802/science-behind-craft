import type { ReactionStep } from "@/lib/explainerMatter";
import { REACTION_KIND_LABEL, speciesName } from "@/lib/processView";
import type { ReactionSpecies } from "@/lib/scienceContract";

export const STEP_SECONDS = 4;

export type Playback = { at: number; playing: boolean };
export type PlaybackAction = { type: "play" | "pause" | "next" | "previous" | "tick" } | { type: "choose"; index: number };
export type CastRole = ReactionSpecies["role"];
export type CastMember = { key: string; formula: string | null; name: string };
export type StepSignal = "BALANCED" | "UNBALANCED";

export const PLAYBACK_START: Playback = { at: 0, playing: false };

export const CAST_ROLE_LABEL: Record<CastRole, string> = { REACTANT: "Reactant", PRODUCT: "Product" };

function stepIndex(index: number, count: number): number {
  return Math.min(Math.max(0, Math.trunc(index)), Math.max(0, count - 1));
}

export function playable(count: number, reduce: boolean): boolean {
  return count > 1 && !reduce;
}

export function playbackStep(state: Playback, action: PlaybackAction, count: number): Playback {
  const last = count - 1;
  switch (action.type) {
    case "play":
      if (count < 2) return PLAYBACK_START;
      return { at: state.at >= last ? 0 : stepIndex(state.at, count), playing: true };
    case "pause":
      return { at: state.at, playing: false };
    case "next":
      return { at: stepIndex(state.at + 1, count), playing: false };
    case "previous":
      return { at: stepIndex(state.at - 1, count), playing: false };
    case "choose":
      return { at: stepIndex(action.index, count), playing: false };
    case "tick": {
      if (!state.playing) return state;
      const at = stepIndex(state.at + 1, count);
      return { at, playing: at < last };
    }
  }
}

export function castKey(species: ReactionSpecies): string {
  return species.formula ? `formula:${species.formula}` : `name:${speciesName(species).toLowerCase()}`;
}

export function reactionCast(steps: readonly ReactionStep[]): CastMember[] {
  const cast = new Map<string, CastMember>();
  for (const step of steps) {
    for (const species of step.species) {
      const key = castKey(species);
      if (!cast.has(key)) cast.set(key, { key, formula: species.formula, name: speciesName(species) });
    }
  }
  return [...cast.values()];
}

export function stepRoles(step: ReactionStep | null): ReadonlyMap<string, CastRole> {
  return new Map(step ? step.species.map((species) => [castKey(species), species.role] as const) : []);
}

export function stepSignal(step: Pick<ReactionStep, "balanced" | "equation">): StepSignal | null {
  if (step.balanced) return "BALANCED";
  return step.equation !== null ? "UNBALANCED" : null;
}

export function stepKindLabel(step: Pick<ReactionStep, "kind">): string {
  return REACTION_KIND_LABEL[step.kind];
}

export function stepPosition(at: number, count: number): string {
  return `Step ${stepIndex(at, count) + 1} of ${count}`;
}
