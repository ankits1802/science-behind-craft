"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";

import { ApiError } from "@/lib/api";
import { emptyAnswer, reduceAnswer, streamAnswer, type AnswerEvent, type AnswerState, type AskRequest } from "@/lib/answerStream";

type Action = { kind: "reset"; request: AskRequest } | { kind: "event"; event: AnswerEvent } | { kind: "fail"; message: string } | { kind: "clear" };

function reducer(state: AnswerState, action: Action): AnswerState {
  switch (action.kind) {
    case "reset":
      return { ...emptyAnswer(action.request.question, action.request.mode), phase: "matching" };
    case "event":
      return reduceAnswer(state, action.event);
    case "fail":
      return { ...state, phase: "failed", error: action.message };
    case "clear":
      return emptyAnswer();
    default:
      return state;
  }
}

export function useAnswerStream() {
  const [state, dispatch] = useReducer(reducer, undefined, () => emptyAnswer());
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => controller.current?.abort(), []);

  const ask = useCallback(async (request: AskRequest) => {
    controller.current?.abort();
    const mine = new AbortController();
    controller.current = mine;
    dispatch({ kind: "reset", request });
    try {
      await streamAnswer(request, (event) => {
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

  return { state, ask, stop, clear };
}
