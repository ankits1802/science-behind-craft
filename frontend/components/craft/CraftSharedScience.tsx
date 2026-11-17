"use client";

import { useMemo } from "react";

import { CitedReading, ListedSources } from "@/components/answer/CitedReading";
import { ConceptGraphView } from "@/components/answer/learning/ConceptGraphView";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { listedSourceNumbers } from "@/lib/citations";
import type { SharedScience } from "@/lib/sharedScienceContract";

export function CraftSharedScience({ science }: { science: SharedScience }) {
  const reduce = useAppReducedMotion();
  const numbers = useMemo(() => listedSourceNumbers(science.sources), [science]);
  return (
    <CitedReading sources={science.sources} numbers={numbers}>
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-5">
        <section className="panel min-w-0 p-4 md:p-6" aria-label={`Science ${science.craft.name} shares with other crafts`} data-testid="craft-shared-science">
          <ConceptGraphView focus={science.craft} nodes={science.nodes} reduce={reduce} />
        </section>
        <ListedSources sources={science.sources} idPrefix="shared-science-source" />
      </div>
    </CitedReading>
  );
}
