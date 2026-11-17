"use client";

import { CitedText } from "@/components/answer/ProseBlockView";
import type { StageFocus } from "@/components/answer/place/RiverStage";
import type { RegionStoryBlock } from "@/lib/explainerPlace";
import { districtLine } from "@/lib/regionStory";
import { cn } from "@/lib/utils";

function StepNumber({ number, reached }: { number: number; reached: boolean }) {
  return (
    <span
      aria-hidden
      className={cn(
        "grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm font-bold tabular-nums transition-colors duration-500",
        reached ? "bg-purple-700 text-white" : "bg-card text-ink-500 ring-1 ring-line-200"
      )}
    >
      {number}
    </span>
  );
}

export function StorySteps({ block, focus, step }: { block: RegionStoryBlock; focus: StageFocus; step: number | null }) {
  return (
    <ol className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2.5" aria-label="Story" data-testid="story-steps">
      {block.steps.map((entry, index) => {
        const place = districtLine(block, entry.districtLgd);
        const on = step === index;
        const reached = focus.reached[index] ?? true;
        const header = (
          <>
            <StepNumber number={index + 1} reached={reached} />
            <span className="min-w-0 text-xs font-semibold uppercase tracking-wide text-ink-500">{place ?? `Step ${index + 1}`}</span>
          </>
        );
        return (
          <li
            key={entry.sentence.id}
            data-reached={reached ? "true" : "false"}
            data-testid="story-step"
            className={cn(
              "rounded-lg border p-3 transition-colors sm:p-4",
              on ? "border-purple-300 bg-purple-50 dark:border-purple-800 dark:bg-purple-950/40" : "border-line-200 bg-card"
            )}
          >
            {place ? (
              <button type="button" aria-pressed={on} onClick={() => focus.onStep(index)} className="flex min-h-9 w-full items-center gap-3 rounded-md text-left hover:text-purple-700">
                {header}
              </button>
            ) : (
              <div className="flex min-h-9 items-center gap-3">{header}</div>
            )}
            <CitedText id={entry.sentence.id} sentences={[entry.sentence]} className="mt-2 pl-11 text-sm leading-7 text-ink-700" />
          </li>
        );
      })}
    </ol>
  );
}
