export const IN_VIEW_MARGIN = "-20% 0px -20% 0px";

export type PlayState = { at: number; wanted: boolean; seen: boolean; started: boolean; motion: boolean };
export type PlayAction =
  | { type: "seen"; on: boolean; motion: boolean }
  | { type: "still" }
  | { type: "start" }
  | { type: "tick"; count: number }
  | { type: "choose"; at: number }
  | { type: "toggle"; motion: boolean; count: number };

export function nextStop(at: number, count: number): number {
  return count > 0 && at + 1 < count ? at + 1 : 0;
}

export function restingPlay(rest: number): PlayState {
  return { at: rest, wanted: true, seen: false, started: false, motion: false };
}

export function isPlaying(state: PlayState, count: number): boolean {
  return state.motion && state.wanted && state.seen && count > 1;
}

export function played(state: PlayState, action: PlayAction): PlayState {
  switch (action.type) {
    case "seen":
      if (state.seen === action.on && (!action.on || state.motion === action.motion)) return state;
      return { ...state, seen: action.on, motion: action.on ? action.motion : state.motion };
    case "still":
      return state.motion ? { ...state, motion: false } : state;
    case "start":
      return state.started ? state : { ...state, at: 0, started: true };
    case "tick":
      return { ...state, at: nextStop(state.at, action.count) };
    case "choose":
      return { ...state, at: action.at, started: true };
    case "toggle":
      if (!action.motion) return { ...state, motion: false, at: nextStop(state.at, action.count) };
      if (isPlaying(state, action.count)) return { ...state, wanted: false };
      return { ...state, wanted: true, seen: true, motion: true };
  }
}
