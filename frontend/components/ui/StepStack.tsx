import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type StackedStep = { key: string; node: ReactNode };

export function StepStack({ steps, at, testId }: { steps: readonly StackedStep[]; at: number; testId: string }) {
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)]" data-testid={testId} data-at={at}>
      {steps.map((step, index) => {
        const shown = index === at;
        return (
          <div key={step.key} className={cn("col-start-1 row-start-1 min-w-0", shown ? null : "invisible")} aria-hidden={shown ? undefined : true} inert={!shown} data-shown={shown ? "true" : "false"}>
            {step.node}
          </div>
        );
      })}
    </div>
  );
}
