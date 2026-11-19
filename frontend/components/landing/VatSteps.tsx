"use client";

import { useId } from "react";

import { TextLink } from "@/components/ui/TextLink";
import type { VatPhase } from "@/lib/motion";

export const VAT_PLAYED_KEY = "kv-vat-played";

type VatStep = Exclude<VatPhase, "rest">;

export const VAT_STEPS: readonly { step: VatStep; label: string }[] = [
  { step: "in", label: "In the vat" },
  { step: "lifted", label: "Lifted, green" },
  { step: "air", label: "Blue in the air" }
];

export const VAT_STATUS: Record<VatPhase, string> = {
  rest: "The cloth is blue in the air.",
  in: "In the vat: the dissolved dye soaks into the fibre.",
  lifted: "Lifted out: the cloth is bright green.",
  air: "In the air the cloth turns blue, from the top down."
};

export function currentVatStep(phase: VatPhase): VatStep {
  return phase === "rest" ? "air" : phase;
}

export function VatSteps({ phase, onPlay }: { phase: VatPhase; onPlay: () => void }) {
  const statusId = useId();
  const current = currentVatStep(phase);
  return (
    <>
      <div className="kv-vat-row">
        <ol className="kv-steps" aria-label="What the cloth does after the vat">
          {VAT_STEPS.map((entry, index) => (
            <li key={entry.step} aria-current={entry.step === current ? "step" : undefined} data-step={entry.step}>
              <b>{index + 1}</b>
              {entry.label}
            </li>
          ))}
        </ol>
        <TextLink onClick={onPlay} describedBy={statusId} className="kv-vat-again">
          Play again
        </TextLink>
      </div>
      <p className="sr-only" id={statusId} role="status">
        {VAT_STATUS[phase]}
      </p>
    </>
  );
}
