"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";

import { ApiError } from "@/lib/api";
import type { AskRequest } from "@/lib/answerStream";
import { askingExplainer, emptyExplainer, reduceExplainer, type ExplainerState } from "@/lib/explainerState";
import { streamExplainer, type ExplainerEvent } from "@/lib/explainerStream";

type Action = { kind: "reset"; request: AskRequest } | { kind: "event"; event: ExplainerEvent } | { kind: "fail"; message: string } | { kind: "clear" };

function reducer(state: ExplainerState, action: Action): ExplainerState {
  switch (action.kind) {
    case "reset":
      return askingExplainer(action.request.question, action.request.language ?? "en");
    case "event":
      return reduceExplainer(state, action.event);
    case "fail":
      return { ...state, phase: "failed", status: null, error: action.message };
    case "clear":
      return emptyExplainer();
    default:
      return state;
  }
}

export function useAnswerStream() {
  const [state, dispatch] = useReducer(reducer, undefined, () => emptyExplainer());
  const [round, setRound] = useState(0);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => controller.current?.abort(), []);

  const ask = useCallback(async (request: AskRequest) => {
    controller.current?.abort();
    const mine = new AbortController();
    controller.current = mine;
    setRound((value) => value + 1);
    dispatch({ kind: "reset", request });
    try {
      await streamExplainer(request, (event) => {
        if (!mine.signal.aborted) dispatch({ kind: "event", event });
      }, mine.signal);
      if (!mine.signal.aborted) dispatch({ kind: "event", event: { type: "done", data: { answerId: null } } });
    } catch (err) {
      if (mine.signal.aborted) return;
      dispatch({ kind: "fail", message: err instanceof ApiError || err instanceof Error ? err.message : "Couldn't answer that. Try again." });
    }
  }, []);

  const stop = useCallback(() => {
    controller.current?.abort();
    controller.current = null;
    dispatch({ kind: "event", event: { type: "done", data: { answerId: null } } });
  }, []);

  const clear = useCallback(() => {
    controller.current?.abort();
    dispatch({ kind: "clear" });
  }, []);

  return { state, round, ask, stop, clear };
}
