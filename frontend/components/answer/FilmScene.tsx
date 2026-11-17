"use client";

import { createContext, useContext } from "react";

export type FilmSceneState = { progress: number };

const FilmSceneContext = createContext<FilmSceneState | null>(null);

export const FilmSceneProvider = FilmSceneContext.Provider;

export function useFilmScene(): FilmSceneState | null {
  return useContext(FilmSceneContext);
}
