import { CircleAlert, CircleCheck } from "lucide-react";

import { GATE_LABELS, type GateReport } from "@/lib/ownProposalsContract";

export function GateResults({ gates }: { gates: GateReport[] }) {
  if (!gates.length) return null;
  return (
    <ol className="grid gap-2" aria-label="What the checks said" data-testid="gate-results">
      {gates.map((gate) => (
        <li key={gate.gate} className="grid grid-cols-[auto_1fr] items-start gap-x-2 font-ui text-label">
          {gate.passed ? (
            <CircleCheck className="mt-0.5 h-4 w-4 text-ink-2" aria-hidden />
          ) : (
            <CircleAlert className="mt-0.5 h-4 w-4 text-error" aria-hidden />
          )}
          <span className="text-ink-1">
            {GATE_LABELS[gate.gate]}: {gate.passed ? "passed" : "refused"}
          </span>
          {gate.reasons.length ? (
            <ul className="col-start-2 grid gap-1 text-ink-2">
              {gate.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
