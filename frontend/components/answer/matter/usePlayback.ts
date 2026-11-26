"use client";

import { useEffect, useReducer } from "react";

import { PLAYBACK_START, playbackStep, STEP_SECONDS, type Playback, type PlaybackAction } from "@/lib/reactionPlayer";

export type PlaybackControls = Playback & { send: (action: PlaybackAction) => void };

export function usePlayback(count: number, running: boolean, start: Playback = PLAYBACK_START): PlaybackControls {
  const [state, send] = useReducer((current: Playback, action: PlaybackAction) => playbackStep(current, action, count), start);
  const playing = running && state.playing;

  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(() => send({ type: "tick" }), STEP_SECONDS * 1000);
    return () => window.clearTimeout(timer);
  }, [playing, state.at]);

  return { at: state.at, playing, send };
}
