import type { KitMotion } from "@/lib/artKit";
import { MOTION_CLASS, parseDuration, type NamedMotion } from "@/lib/motion";

export type KitTimings = { dip: number; hold: number; oxidise: number };
export type KitBeat = { panel: number | null; moves: boolean; at: number };

export const KIT_NAMED_MOTION: Readonly<Record<KitMotion, NamedMotion>> = { dip: "dip", take: "dip", dry: "oxidise" };
export const KIT_TIMING_TOKENS: Readonly<Record<keyof KitTimings, string>> = { dip: "--dur-dip", hold: "--dur-hold", oxidise: "--dur-oxidise" };

export function kitMotionClass(motion: KitMotion): string {
  return MOTION_CLASS[KIT_NAMED_MOTION[motion]];
}

export function kitTimings(read: (token: string) => string): KitTimings {
  return {
    dip: parseDuration(read(KIT_TIMING_TOKENS.dip)),
    hold: parseDuration(read(KIT_TIMING_TOKENS.hold)),
    oxidise: parseDuration(read(KIT_TIMING_TOKENS.oxidise))
  };
}

export function kitBeatLength(motion: KitMotion | null, timings: KitTimings): number {
  if (motion === null) return timings.hold;
  return KIT_NAMED_MOTION[motion] === "oxidise" ? timings.oxidise : timings.dip;
}

export function kitSchedule(motions: readonly (KitMotion | null)[], timings: KitTimings): KitBeat[] {
  const beats: KitBeat[] = [];
  let at = 0;
  motions.forEach((motion, panel) => {
    beats.push({ panel, moves: motion !== null, at });
    at += kitBeatLength(motion, timings) + timings.hold;
  });
  beats.push({ panel: null, moves: false, at });
  return beats;
}

export function kitStillStep(current: number | null, count: number): number | null {
  if (current === null) return count > 0 ? 0 : null;
  return current + 1 < count ? current + 1 : null;
}

export function kitStatus(panel: number | null, labels: readonly string[]): string {
  if (panel === null) return "At rest";
  const step = `Step ${panel + 1} of ${labels.length}`;
  return labels[panel] ? `${step}: ${labels[panel]}` : step;
}
