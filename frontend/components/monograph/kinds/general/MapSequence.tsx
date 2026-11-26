"use client";

import type { ReactNode } from "react";

import { useMotionAllowed } from "@/components/motion/useMotionAllowed";
import { PlayPauseButton } from "@/components/ui/PlayPauseButton";
import type { MapStepSpec } from "@/lib/componentSpecsMapLayer";
import { stepPosition } from "@/lib/reactionPlayer";
import { cn } from "@/lib/utils";

import type { SequenceControls } from "./useMapSequence";

export const STEPS_LABEL = "Steps of the map";

type SequenceProps = { steps: readonly MapStepSpec[]; play: SequenceControls; renderUnit: (ref: string) => ReactNode };

const STEP = "grid size-11 place-items-center rounded-full font-ui text-label font-medium transition-colors duration-state [font-variant-numeric:lining-nums_tabular-nums]";

export function MapSequence({ steps, play, renderUnit }: SequenceProps) {
  const motion = useMotionAllowed();
  return (
    <div className="grid min-w-0 gap-2" data-testid="map-sequence" data-plays="view">
      <div className="flex min-w-0 items-center gap-3">
        <PlayPauseButton playing={play.playing} motion={motion} onToggle={play.toggle} testId="map-sequence-play" />
        <p className="font-ui text-label text-ink-2 [font-variant-numeric:lining-nums_tabular-nums]" role="status" aria-live={play.playing ? "off" : "polite"} data-testid="map-sequence-status">
          {stepPosition(play.at, steps.length)}
        </p>
      </div>
      <ol className="grid min-w-0" aria-label={STEPS_LABEL} data-testid="map-steps">
        {steps.map((step, at) => {
          const chosen = at === play.at;
          return (
            <li key={step.text} className={cn("grid grid-cols-[2.75rem_minmax(0,1fr)] items-start gap-3 border-t border-rule py-2", chosen ? "border-s-2 border-s-ink-1 ps-2" : null)} aria-current={chosen ? "step" : undefined}>
              <button
                type="button"
                className={cn(STEP, chosen ? "bg-indigo text-indigo-on" : "border border-rule-strong bg-raised text-ink-1 hover:bg-sunk")}
                aria-pressed={chosen}
                aria-label={`Show step ${at + 1} of ${steps.length}`}
                onClick={() => play.choose(at)}
                data-testid="map-step"
              >
                {at + 1}
              </button>
              <div className={cn("min-w-0 pt-2.5 font-reading text-body-sm", chosen ? "text-ink-1" : "text-ink-2")} data-testid="map-step-text">
                {renderUnit(step.text)}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
