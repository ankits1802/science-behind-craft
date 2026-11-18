"use client";

import { createContext, useContext } from "react";

const FieldLabelContext = createContext<string | undefined>(undefined);

export const FieldLabelProvider = FieldLabelContext.Provider;

export function useFieldLabelId(): string | undefined {
  return useContext(FieldLabelContext);
}

export type FieldState = { describedBy?: string; invalid: boolean };

const FieldStateContext = createContext<FieldState>({ invalid: false });

export const FieldStateProvider = FieldStateContext.Provider;

export function useFieldState(): FieldState {
  return useContext(FieldStateContext);
}
