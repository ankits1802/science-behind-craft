export type KitIds = { base: string; weave: string; grain: string; strata: string; speckle: string; ripple: string };

export type PartIds = KitIds & { part: string };

export type Moving = { className: string; panel: number };

export function kitIds(label: string): KitIds {
  const base = `kit-${label.replace(/[^A-Za-z0-9_-]+/g, "-")}`;
  return { base, weave: `${base}-weave`, grain: `${base}-grain`, strata: `${base}-strata`, speckle: `${base}-speckle`, ripple: `${base}-ripple` };
}

export function partIds(ids: KitIds, key: string): PartIds {
  return { ...ids, part: `${ids.base}-${key}` };
}

export function paint(token: string): string {
  return `var(${token})`;
}

export function url(id: string): string {
  return `url(#${id})`;
}
