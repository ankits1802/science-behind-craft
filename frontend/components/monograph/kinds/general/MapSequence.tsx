"use client";

import type { ReactNode } from "react";
import { Pause, Play } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { MapStepSpec } from "@/lib/componentSpecsMapLayer";
import { cn } from "@/lib/utils";

import type { SequenceControls } from "./useMapSequence";

export const STEPS_LABEL = "Steps of the map";

type SequenceProps = { steps: readonly MapStepSpec[]; play: SequenceControls; renderUnit: (ref: string) => ReactNode; nameOf: (ref: string) => string };

const STEP = "grid size-11 place-items-center rounded-full font-ui text-label font-medium transition-colors duration-state [font-variant-numeric:lining-nums_tabular-nums]";

export function MapSequence({ steps, play, renderUnit, nameOf }: SequenceProps) {
  const current = steps[play.at];
  return (
    <div className="grid min-w-0 gap-2 border-t border-rule pt-3" data-testid="map-sequence">
      <div className="flex min-w-0 flex-wrap items-center gap-3">
        <Button variant="quiet" size="sm" onClick={play.toggle} data-testid="map-sequence-play">
          {play.playing ? <Pause className="size-3.5" aria-hidden /> : <Play className="size-3.5" aria-hidden />}
          <span>{play.playing ? "Pause" : "Play"}</span>
        </Button>
        <ol className="flex min-w-0 flex-wrap items-center gap-1" aria-label={STEPS_LABEL} data-testid="map-steps">
          {steps.map((step, at) => {
            const chosen = at === play.at;
            return (
              <li key={step.text}>
                <button
                  type="button"
                  className={cn(STEP, chosen ? "bg-indigo text-indigo-on" : "border border-rule-strong bg-raised text-ink-1 hover:bg-sunk")}
                  aria-pressed={chosen}
                  aria-label={`Step ${at + 1} of ${steps.length}: ${nameOf(step.text)}`}
                  onClick={() => play.choose(at)}
                  data-testid="map-step"
                >
                  {at + 1}
                </button>
              </li>
            );
          })}
        </ol>
      </div>
      <div className="font-reading text-body-sm text-ink-1" aria-live={play.playing ? "off" : "polite"} data-testid="map-step-text">
        {current ? renderUnit(current.text) : null}
      </div>
    </div>
  );
}
