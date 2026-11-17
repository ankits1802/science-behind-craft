"use client";

import { useCallback, useState } from "react";

import { ApiError, apiErrorMessage } from "@/lib/api";
import { fetchListenScript, LISTEN_RATES, listenMark, nextRate, type ListenMark, type ListenPosition, type ListenScript } from "@/lib/listen";

export type ListenStatus = "idle" | "loading" | "playing" | "paused" | "failed";

export type Listen = {
  status: ListenStatus;
  script: ListenScript | null;
  position: ListenPosition;
  rate: number;
  error: string | null;
  mark: ListenMark | null;
  start: () => void;
  toggle: () => void;
  stop: () => void;
  cycleRate: () => void;
  onTime: (time: number) => void;
  onEnded: () => void;
  onBroken: () => void;
  onRefused: () => void;
};

const START = { track: 0, time: 0 };
const FAILED_TO_START = "Couldn't start listening. Try again.";
const FAILED_TO_PLAY = "Couldn't play the audio. Try again.";

export function useListen(answerId: string | null, language: string): Listen {
  const [script, setScript] = useState<ListenScript | null>(null);
  const [status, setStatus] = useState<ListenStatus>("idle");
  const [position, setPosition] = useState<ListenPosition>(START);
  const [rate, setRate] = useState<number>(LISTEN_RATES[0]);
  const [error, setError] = useState<string | null>(null);

  const fail = useCallback((message: string) => {
    setError(message);
    setStatus("failed");
  }, []);

  const start = useCallback(() => {
    if (!answerId) return;
    setError(null);
    if (script) {
      setStatus("playing");
      return;
    }
    setStatus("loading");
    fetchListenScript(answerId, language)
      .then((loaded) => {
        setScript(loaded);
        setPosition(START);
        setStatus("playing");
      })
      .catch((cause: unknown) => {
        if (!(cause instanceof ApiError)) console.error(cause);
        fail(apiErrorMessage(cause, FAILED_TO_START));
      });
  }, [answerId, language, script, fail]);

  const stop = useCallback(() => {
    setPosition(START);
    setStatus("idle");
    setError(null);
  }, []);

  const toggle = useCallback(() => {
    if (status === "playing") setStatus("paused");
    else if (status === "paused") setStatus("playing");
    else start();
  }, [status, start]);

  const onTime = useCallback((time: number) => setPosition((current) => ({ track: current.track, time })), []);

  const onEnded = useCallback(() => {
    if (script && position.track + 1 < script.tracks.length) setPosition({ track: position.track + 1, time: 0 });
    else stop();
  }, [script, position.track, stop]);

  const onBroken = useCallback(() => {
    setScript(null);
    fail(FAILED_TO_PLAY);
  }, [fail]);

  const onRefused = useCallback(() => fail(FAILED_TO_PLAY), [fail]);

  const mark = status === "playing" || status === "paused" ? listenMark(script, position) : null;
  return { status, script, position, rate, error, mark, start, toggle, stop, cycleRate: () => setRate(nextRate), onTime, onEnded, onBroken, onRefused };
}
