"use client";

import { useState, type ReactNode } from "react";

import { Demo, Grid, Section } from "@/app/design/DesignParts";
import { motionClass, useNamedMotion } from "@/components/motion/useNamedMotion";
import { useVatMoment } from "@/components/motion/useVatMoment";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import type { VatPhase } from "@/lib/motion";

const PHASE_WORDS: Record<VatPhase, string> = {
  rest: "The cloth is blue in the air.",
  in: "In the vat: the dissolved dye soaks into the fibre.",
  lifted: "Lifted: the cloth is bright green.",
  air: "In the air: the cloth turns from green to blue."
};

const STEPS: { phase: VatPhase; label: string }[] = [
  { phase: "in", label: "In the vat" },
  { phase: "lifted", label: "Lifted, green" },
  { phase: "air", label: "Blue in the air" }
];

function Swatch({ base, children }: { base: string; children?: ReactNode }) {
  return (
    <span className="block rounded-plate border border-ink-2 bg-raised p-0.5 [forced-color-adjust:none]">
      <span className="relative block h-24 w-36 overflow-hidden" style={{ background: `var(${base})` }}>
        {children}
      </span>
    </span>
  );
}

function NamedDemo({ name, base, layer, caption }: { name: "dip" | "oxidise"; base: string; layer: string; caption: string }) {
  const [layerRef, play] = useNamedMotion<HTMLSpanElement>();
  return (
    <Demo caption={caption}>
      <Swatch base={base}>
        <span ref={layerRef} className={`absolute inset-0 ${motionClass(name)}`} style={{ background: `var(${layer})` }} />
      </Swatch>
      <ActionGroup align="start" className="mt-4">
        <Button variant="quiet" size="sm" onClick={play}>Play</Button>
      </ActionGroup>
    </Demo>
  );
}

function PressDemo() {
  const [pressRef, play] = useNamedMotion<HTMLButtonElement>();
  const [saved, setSaved] = useState(false);
  return (
    <Demo caption="Press, 120ms">
      <Button
        ref={pressRef}
        variant="quiet"
        className={motionClass("press")}
        aria-pressed={saved}
        onClick={() => {
          setSaved(!saved);
          play();
        }}
      >
        {saved ? "Saved" : "Save"}
      </Button>
    </Demo>
  );
}

function VatDemo() {
  const [status, setStatus] = useState(PHASE_WORDS.rest);
  const vat = useVatMoment({ onPhase: (phase) => setStatus(PHASE_WORDS[phase]) });
  const current = vat.phase === "rest" ? "air" : vat.phase;
  return (
    <Demo caption="The vat, 2600ms: dip, hold, oxidise">
      <div className="flex flex-wrap items-start gap-6" data-vat-phase={vat.phase}>
        <Swatch base="--dye-indigo">
          <span className="vat-tint absolute inset-0 mix-blend-color" style={{ background: "var(--dye-leuco)" }} />
        </Swatch>
        <div className="grid min-w-0 gap-3">
          <ol className="grid grid-cols-3 gap-1.5" aria-label="What the cloth does after the vat">
            {STEPS.map((step, index) => (
              <li key={step.phase} aria-current={step.phase === current ? "step" : undefined} className="grid gap-0.5 border-t-2 border-rule pt-1.5 font-ui text-caption text-ink-3 aria-[current=step]:border-ink-1 aria-[current=step]:font-semibold aria-[current=step]:text-ink-1">
                <b className="font-semibold">{index + 1}</b>
                {step.label}
              </li>
            ))}
          </ol>
          <p role="status" className="font-ui text-ui font-normal text-ink-2">{status}</p>
          <Button variant="text" onClick={vat.play}>Play again</Button>
        </div>
      </div>
    </Demo>
  );
}

export function MotionSection() {
  return (
    <Section id="motion" title="Motion" lede="Motion runs only to explain a reaction or a process. Each end state is the resting style, so with reduced motion every demo shows its end at once and every control still works.">
      <Grid columns={3}>
        <NamedDemo name="dip" base="--dye-cloth" layer="--dye-harda" caption="Dip, 600ms" />
        <NamedDemo name="oxidise" base="--dye-indigo" layer="--dye-leuco" caption="Oxidise, 1500ms" />
        <PressDemo />
      </Grid>
      <VatDemo />
    </Section>
  );
}
