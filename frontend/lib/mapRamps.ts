import type { MapLayer, MapLayerSummary } from "@/lib/regionContract";

export const RAMP_STEPS = 6;
export const NO_READING_LABEL = "No reading in the dataset";

export type RampName = "rain" | "heat" | "density";

const RAMP_BY_VARIABLE: readonly [RegExp, RampName][] = [
  [/rain|precip/i, "rain"],
  [/temp/i, "heat"]
];

export function layerRamp(layer: Pick<MapLayerSummary, "variable">): RampName {
  return RAMP_BY_VARIABLE.find(([pattern]) => pattern.test(layer.variable))?.[1] ?? "density";
}

export function rampStep(classIndex: number, classCount: number): number {
  if (classCount < 1 || classIndex < 0 || classIndex >= classCount) throw new RangeError(`class ${classIndex} of ${classCount}`);
  if (classCount === 1) return Math.ceil(RAMP_STEPS / 2);
  return 1 + Math.round((classIndex * (RAMP_STEPS - 1)) / (classCount - 1));
}

export function rampColour(ramp: RampName, step: number): string {
  return `var(--${ramp}-${step})`;
}

export function classColour(layer: MapLayer, classIndex: number): string {
  return rampColour(layerRamp(layer.layer), rampStep(classIndex, layer.classes.length));
}

export function layerColours(layer: MapLayer): string[] {
  return layer.classes.map((_, at) => classColour(layer, at));
}
