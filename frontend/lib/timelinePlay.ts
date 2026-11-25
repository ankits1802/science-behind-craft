export const TIMELINE_STEP_MS = 3200;
export const POINT_GAP_PERCENT = 6;

const FULL = 100;
const MIDDLE = 50;

export type PlayState = { at: number; wanted: boolean; seen: boolean; started: boolean };
export type PlayAction =
  | { type: "seen"; on: boolean }
  | { type: "start" }
  | { type: "tick"; count: number }
  | { type: "choose"; at: number }
  | { type: "toggle"; motion: boolean; count: number };

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

export function nextStop(at: number, count: number): number {
  return count > 0 && at + 1 < count ? at + 1 : 0;
}

export function restingPlay(rest: number): PlayState {
  return { at: rest, wanted: true, seen: false, started: false };
}

export function isPlaying(state: PlayState, motion: boolean, count: number): boolean {
  return motion && state.wanted && state.seen && count > 1;
}

export function played(state: PlayState, action: PlayAction): PlayState {
  switch (action.type) {
    case "seen":
      return { ...state, seen: action.on };
    case "start":
      return state.started ? state : { ...state, at: 0, started: true };
    case "tick":
      return { ...state, at: nextStop(state.at, action.count) };
    case "choose":
      return { ...state, at: action.at, started: true };
    case "toggle":
      if (!action.motion) return { ...state, at: nextStop(state.at, action.count) };
      if (isPlaying(state, action.motion, action.count)) return { ...state, wanted: false };
      return { ...state, wanted: true, seen: true };
  }
}
