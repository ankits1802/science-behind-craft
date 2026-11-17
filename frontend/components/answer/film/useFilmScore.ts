"use client";

import { useCallback, useRef, useState } from "react";

import { ApiError, apiErrorMessage } from "@/lib/api";
import { fetchFilmScore, type FilmScore } from "@/lib/filmScore";

export const SCORE_FAILED = "Couldn't load the music. Try again.";

export type FilmScoreState = { on: boolean; score: FilmScore | null; loading: boolean; error: string | null; toggle: (next: boolean) => void };

export function useFilmScore(answerId: string, language: string): FilmScoreState {
  const [on, setOn] = useState(false);
  const [score, setScore] = useState<FilmScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const asked = useRef(false);

  const toggle = useCallback(
    (next: boolean) => {
      setOn(next);
      setError(null);
      if (!next || asked.current) return;
      asked.current = true;
      setLoading(true);
      fetchFilmScore(answerId, language)
        .then(setScore)
        .catch((cause: unknown) => {
          if (!(cause instanceof ApiError)) console.error(cause);
          asked.current = false;
          setOn(false);
          setError(apiErrorMessage(cause, SCORE_FAILED));
        })
        .finally(() => setLoading(false));
    },
    [answerId, language]
  );

  return { on, score: on ? score : null, loading, error, toggle };
}
