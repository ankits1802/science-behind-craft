"use client";

import { createContext, useContext } from "react";

const AnswerIdContext = createContext<string | null>(null);

export const AnswerIdProvider = AnswerIdContext.Provider;

export function useAnswerId(): string | null {
  return useContext(AnswerIdContext);
}
