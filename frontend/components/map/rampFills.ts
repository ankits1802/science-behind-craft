import type { RampName } from "@/lib/mapRamps";

export const RAMP_FILLS: Record<RampName, readonly string[]> = {
  rain: ["fill-[var(--rain-1)]", "fill-[var(--rain-2)]", "fill-[var(--rain-3)]", "fill-[var(--rain-4)]", "fill-[var(--rain-5)]", "fill-[var(--rain-6)]"],
  heat: ["fill-[var(--heat-1)]", "fill-[var(--heat-2)]", "fill-[var(--heat-3)]", "fill-[var(--heat-4)]", "fill-[var(--heat-5)]", "fill-[var(--heat-6)]"],
  density: ["fill-[var(--density-1)]", "fill-[var(--density-2)]", "fill-[var(--density-3)]", "fill-[var(--density-4)]", "fill-[var(--density-5)]", "fill-[var(--density-6)]"]
};

export function rampFill(ramp: RampName, step: number): string {
  return RAMP_FILLS[ramp][Math.min(Math.max(step, 1), RAMP_FILLS[ramp].length) - 1];
}

export const CHOROPLETH_COLOURS = ["var(--density-1)", "var(--density-2)", "var(--density-3)", "var(--density-5)", "var(--density-6)"] as const;
