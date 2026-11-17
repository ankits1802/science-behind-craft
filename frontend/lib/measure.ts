export type MeasureParts = { prefix: string; suffix: string; scale: number };

const UNIT_TEXT: Record<string, string> = {
  degC: "°C",
  "degC per decade": "°C per decade",
  m2: "m²",
  l: "L",
  km2: "km²",
  "km/km2": "km/km²",
  "m3/s": "m³/s"
};

const MAX_DECIMALS = 2;

export function measureParts(unit: string): MeasureParts {
  const trimmed = unit.trim();
  if (trimmed === "pH") return { prefix: "pH ", suffix: "", scale: 1 };
  if (trimmed === "%") return { prefix: "", suffix: "%", scale: 1 };
  if (trimmed.startsWith("fraction")) {
    const rest = trimmed.slice("fraction".length).trim();
    return { prefix: "", suffix: rest ? `% ${rest}` : "%", scale: 100 };
  }
  const shown = UNIT_TEXT[trimmed] ?? trimmed;
  return { prefix: "", suffix: shown ? ` ${shown}` : "", scale: 1 };
}

export function decimalsOf(value: number): number {
  if (!Number.isFinite(value)) throw new RangeError(`${value} is not a finite number`);
  const rounded = Number(value.toFixed(MAX_DECIMALS));
  const text = String(rounded);
  const point = text.indexOf(".");
  return point < 0 ? 0 : Math.min(MAX_DECIMALS, text.length - point - 1);
}

export function sharedDecimals(values: readonly number[]): number {
  return values.reduce((most, value) => Math.max(most, decimalsOf(value)), 0);
}

export function formatNumber(value: number, decimals: number = decimalsOf(value)): string {
  const text = new Intl.NumberFormat("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value);
  return text.replace(/^-/, "−");
}

function scaled(value: number, parts: MeasureParts): number {
  return Number((value * parts.scale).toFixed(6));
}

export function formatMeasure(value: number, unit: string): string {
  const parts = measureParts(unit);
  const shown = scaled(value, parts);
  return `${parts.prefix}${formatNumber(shown)}${parts.suffix}`;
}

export function formatRange(min: number | null, max: number | null, unit: string): string | null {
  const parts = measureParts(unit);
  const low = min === null ? null : scaled(min, parts);
  const high = max === null ? null : scaled(max, parts);
  const decimals = sharedDecimals([low, high].filter((value): value is number => value !== null));
  const text = (value: number) => formatNumber(value, decimals);
  if (low !== null && high !== null) {
    const body = low === high ? text(low) : `${text(low)}–${text(high)}`;
    return `${parts.prefix}${body}${parts.suffix}`;
  }
  if (high !== null) return `≤ ${parts.prefix}${text(high)}${parts.suffix}`;
  if (low !== null) return `≥ ${parts.prefix}${text(low)}${parts.suffix}`;
  return null;
}
