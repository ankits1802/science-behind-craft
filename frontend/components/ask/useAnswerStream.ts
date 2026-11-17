"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";

import { ApiError } from "@/lib/api";
import type { AskRequest } from "@/lib/answerStream";
import { askingExplainer, emptyExplainer, type ExplainerRef, type ExplainerState } from "@/lib/explainerState";
import { streamExplainer, type ExplainerEvent } from "@/lib/explainerStream";
import { followingExplainer, reduceAnswerEvent } from "@/lib/explainerVersions";

type Action =
  | { kind: "reset"; request: AskRequest }
  | { kind: "follow"; ref: ExplainerRef; question: string }
  | { kind: "load"; state: ExplainerState }
  | { kind: "event"; event: ExplainerEvent }
  | { kind: "fail"; message: string }
  | { kind: "clear" };

function reducer(state: ExplainerState, action: Action): ExplainerState {
  switch (action.kind) {
    case "reset":
      return askingExplainer(action.request.question, action.request.language ?? "en");
    case "follow":
      return followingExplainer(state, action.ref, action.question);
    case "load":
      return action.state;
    case "event":
      return reduceAnswerEvent(state, action.event);
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

  const stream = useCallback(async (request: AskRequest, start: Action) => {
    controller.current?.abort();
    const mine = new AbortController();
    controller.current = mine;
    dispatch(start);
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

  const ask = useCallback(
    (request: AskRequest) => {
      setRound((value) => value + 1);
      return stream(request, { kind: "reset", request });
    },
    [stream]
  );

  const follow = useCallback((request: AskRequest, ref: ExplainerRef) => stream(request, { kind: "follow", ref, question: request.question }), [stream]);

  const load = useCallback((next: ExplainerState) => {
    controller.current?.abort();
    controller.current = null;
    setRound((value) => value + 1);
    dispatch({ kind: "load", state: next });
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

  return { state, round, ask, follow, load, stop, clear };
}
