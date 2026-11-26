export const TIMELINE_STEP_MS = 3200;
export const POINT_GAP_PERCENT = 6;

const FULL = 100;
const MIDDLE = 50;

export function timelineBeat(): number {
  return TIMELINE_STEP_MS;
}

export function pointPositions(values: readonly number[]): number[] {
  if (values.length === 0) return [];
  const first = Math.min(...values);
  const span = Math.max(...values) - first;
  return values.map((value) => (span > 0 ? ((value - first) / span) * FULL : MIDDLE));
}

export function spreadPositions(positions: readonly number[], gap: number = POINT_GAP_PERCENT): number[] {
  if (positions.length < 2) return [...positions];
  const room = Math.min(gap, FULL / (positions.length - 1));
  const spread = positions.map((position) => Math.min(FULL, Math.max(0, position)));
  for (let at = 1; at < spread.length; at += 1) spread[at] = Math.max(spread[at], spread[at - 1] + room);
  spread[spread.length - 1] = Math.min(spread[spread.length - 1], FULL);
  for (let at = spread.length - 2; at >= 0; at -= 1) spread[at] = Math.min(spread[at], spread[at + 1] - room);
  return spread.map((position) => Math.round(position * 100) / 100);
}
