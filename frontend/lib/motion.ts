export type NamedMotion = "press" | "dip" | "oxidise";

export const MOTION_CLASS: Record<NamedMotion, string> = {
  press: "motion-press",
  dip: "motion-dip",
  oxidise: "motion-oxidise"
};

export const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

export type MotionSwitches = { system: boolean; setting: boolean };

export type VatPhase = "rest" | "in" | "lifted" | "air";

export type VatTimings = { delay: number; dip: number; hold: number; oxidise: number };

export type VatStep = { phase: VatPhase; at: number };

export const VAT_STILL_STEP: Record<VatPhase, VatPhase> = { rest: "in", in: "lifted", lifted: "air", air: "rest" };

export const VAT_TOKENS: Record<keyof VatTimings, string> = {
  delay: "--dur-vat-delay",
  dip: "--dur-dip",
  hold: "--dur-hold",
  oxidise: "--dur-oxidise"
};

export function motionReduced(switches: MotionSwitches): boolean {
  return switches.system || switches.setting;
}

export function motionSwitches(root: { dataset: DOMStringMap } | null, media: { matches: boolean } | null): MotionSwitches {
  return { system: media?.matches ?? false, setting: root?.dataset.reducedMotion === "true" };
}

export function parseDuration(value: string): number {
  const text = value.trim();
  const found = /^(-?(?:\d+(?:\.\d*)?|\.\d+))(ms|s)$/.exec(text);
  if (!found) throw new Error(`Not a CSS duration: "${value}"`);
  const amount = Number(found[1]);
  return found[2] === "s" ? amount * 1000 : amount;
}

export function vatTimings(read: (token: string) => string): VatTimings {
  return {
    delay: parseDuration(read(VAT_TOKENS.delay)),
    dip: parseDuration(read(VAT_TOKENS.dip)),
    hold: parseDuration(read(VAT_TOKENS.hold)),
    oxidise: parseDuration(read(VAT_TOKENS.oxidise))
  };
}

export function vatSchedule(timings: VatTimings, withDelay: boolean): VatStep[] {
  const start = withDelay ? timings.delay : 0;
  return [
    { phase: "in", at: start },
    { phase: "lifted", at: start + timings.dip },
    { phase: "air", at: start + timings.dip + timings.hold },
    { phase: "rest", at: start + timings.dip + timings.hold + timings.oxidise }
  ];
}
