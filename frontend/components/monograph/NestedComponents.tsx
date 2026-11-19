"use client";

import { createContext, useContext, type ReactNode } from "react";

export type NestedComponentRenderer = (label: string) => ReactNode;

export const NestedComponents = createContext<NestedComponentRenderer>(() => null);

export function useNestedComponent(): NestedComponentRenderer {
  return useContext(NestedComponents);
}
