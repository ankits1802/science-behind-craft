import type { KitMotion, SpeciesRole } from "@/lib/artKit";
import { MOTION_CLASS, parseDuration, type NamedMotion } from "@/lib/motion";

export type KitTimings = { dip: number; hold: number; oxidise: number; vat: number };
export type ReactionMove = SpeciesRole | "arrow" | "break";

export const KIT_NAMED_MOTION: Readonly<Record<KitMotion, NamedMotion | null>> = { dip: "dip", take: "dip", dry: "oxidise", react: null };
export const KIT_REACTION_CLASS: Readonly<Record<ReactionMove, string>> = { reactant: "kv-rx-meet", reagent: "kv-rx-arrive", product: "kv-rx-form", arrow: "kv-rx-arrow", break: "kv-rx-break" };
export const KIT_TIMING_TOKENS: Readonly<Record<keyof KitTimings, string>> = { dip: "--dur-dip", hold: "--dur-hold", oxidise: "--dur-oxidise", vat: "--dur-vat" };

export function kitMotionClass(motion: KitMotion): string {
  const named = KIT_NAMED_MOTION[motion];
  return named ? MOTION_CLASS[named] : KIT_REACTION_CLASS.product;
}

export function kitTimings(read: (token: string) => string): KitTimings {
  return {
    dip: parseDuration(read(KIT_TIMING_TOKENS.dip)),
    hold: parseDuration(read(KIT_TIMING_TOKENS.hold)),
    oxidise: parseDuration(read(KIT_TIMING_TOKENS.oxidise)),
    vat: parseDuration(read(KIT_TIMING_TOKENS.vat))
  };
}

export function kitBeatLength(motion: KitMotion | null, timings: KitTimings): number {
  if (motion === null) return timings.hold;
  if (motion === "react") return timings.vat;
  return KIT_NAMED_MOTION[motion] === "oxidise" ? timings.oxidise : timings.dip;
}

export function kitBeat(motions: readonly (KitMotion | null)[], at: number, timings: KitTimings): number {
  return kitBeatLength(motions[at] ?? null, timings) + timings.hold;
}

export function kitPanel(at: number, count: number): number | null {
  return at >= 0 && at < count ? at : null;
}

export function kitStatus(panel: number | null, labels: readonly string[]): string {
  if (panel === null) return "At rest";
  const step = `Step ${panel + 1} of ${labels.length}`;
  return labels[panel] ? `${step}: ${labels[panel]}` : step;
}
