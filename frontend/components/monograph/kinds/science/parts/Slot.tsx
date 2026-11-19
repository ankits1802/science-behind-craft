"use client";

import { createContext, useContext, type ReactNode } from "react";

import type { ComponentSlot } from "@/lib/componentSpecsScienceParts";

export type NestedComponentRenderer = (label: string) => ReactNode;

export const NestedComponents = createContext<NestedComponentRenderer>(() => null);

export function Slot({ slot }: { slot: ComponentSlot }) {
  const render = useContext(NestedComponents);
  return <>{render(slot.component)}</>;
}
