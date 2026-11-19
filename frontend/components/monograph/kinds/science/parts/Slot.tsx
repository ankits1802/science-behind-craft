"use client";

import { useNestedComponent } from "@/components/monograph/NestedComponents";
import type { ComponentSlot } from "@/lib/componentSpecsScienceParts";

export function Slot({ slot }: { slot: ComponentSlot }) {
  const render = useNestedComponent();
  return <>{render(slot.component)}</>;
}
