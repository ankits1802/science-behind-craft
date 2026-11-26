"use client";

import { useCallback, useEffect, useRef } from "react";

import { CitedText } from "@/components/answer/ProseBlockView";
import { ExplainerSentence } from "@/components/answer/ExplainerSentence";
import { SentencesDiffer, SentenceWithReadings } from "@/components/answer/SentencesDiffer";
import { VatArt, type VatArtRefs } from "@/components/answer/VatArt";
import { VatEquationView } from "@/components/answer/VatEquation";
import { FactGrid } from "@/components/editorial/FactGrid";
import { motionAllowedNow } from "@/components/motion/useMotionAllowed";
import { usePlayInView, type PlayInView } from "@/components/motion/usePlayInView";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Figure } from "@/components/ui/Figure";
import { PlayPauseButton } from "@/components/ui/PlayPauseButton";
import type { SaidFact } from "@/lib/answerSignature";
import { dipStatus, vatBeat, VAT_BEATS, VAT_DIPS, VAT_FRAMES, VAT_REST, vatEquation, vatFrameAt, vatShown, vatText, type VatFrame } from "@/lib/answerVat";
import type { IndigoVatBlock } from "@/lib/explainerSignature";
import { vatTimings } from "@/lib/motion";
import { cn } from "@/lib/utils";

const NO_REFS: VatArtRefs = { dipRef: null, airRef: null };

function readToken(token: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(token);
}

function replay(element: Element | null): void {
  if (!element || !motionAllowedNow()) return;
  element.removeAttribute("data-playing");
  void element.getBoundingClientRect();
  element.setAttribute("data-playing", "");
  element.addEventListener("animationend", () => element.removeAttribute("data-playing"), { once: true });
}

type FramesProps = VatArtRefs & { frames: VatFrame[]; current: VatFrame["key"]; dip: number; onChoose: (frame: number) => void };

function Frames({ frames, current, dip, dipRef, airRef, onChoose }: FramesProps) {
  return (
    <ol className="grid grid-cols-1 overflow-hidden rounded-plate border border-ink-1 md:grid-cols-3" data-testid="vat-frames">
      {frames.map((frame, index) => {
        const on = frame.key === current;
        return (
          <li
            key={frame.key}
            aria-current={on ? "step" : undefined}
            className={cn(
              "relative grid min-w-0 grid-cols-[112px_minmax(0,1fr)] content-start gap-x-3.5 bg-raised pb-3 pe-3.5 md:block md:pb-4.5 md:pe-0",
              index > 0 ? "border-t border-rule md:border-t-0 md:border-s" : null
            )}
            data-frame={frame.key}
          >
            {on ? <span aria-hidden className="absolute inset-x-0 top-0 h-0.5 bg-ink-1" /> : null}
            <div className="row-span-3">
              <VatArt frame={frame.key} dip={dip} dipRef={dipRef} airRef={airRef} />
            </div>
            <p className="mt-1 font-ui text-caption font-semibold tabular-nums text-ink-3 md:mx-4.5 md:mt-3">{index + 1}</p>
            <h3 className={cn("mt-1 font-reading text-body text-ink-1 md:mx-4.5 md:text-h3", on ? "font-semibold" : null)}>
              <button type="button" aria-pressed={on} onClick={() => onChoose(index)} className="min-h-target rounded-control text-start hover:text-indigo-hover" data-testid="vat-frame">
                {frame.title}
              </button>
            </h3>
            {frame.sentence ? <CitedText id={`vat-${frame.key}`} sentences={[frame.sentence]} className="mt-1.5 font-reading text-figcaption text-ink-2 md:mx-4.5 md:text-body-sm" /> : null}
          </li>
        );
      })}
    </ol>
  );
}

function VatFacts({ block, said }: { block: IndigoVatBlock; said: readonly SaidFact[] }) {
  const facts = said.map((fact) => ({ label: fact.label, value: <SentenceWithReadings sentence={fact.sentence} /> }));
  if (facts.length === 0) return null;
  return (
    <section className="mt-6" aria-label={block.vat === "FERMENTED" ? "What the fermented vat holds" : "What the vat holds"}>
      <p className="kicker mb-2">{block.vat === "FERMENTED" ? "A fermented vat holds" : "A chemical vat holds"}</p>
      <FactGrid facts={facts} columns={2} />
    </section>
  );
}

function VatStatus({ text, playing }: { text: string; playing: boolean }) {
  return (
    <div className="grid w-full font-ui text-ui font-normal text-ink-2">
      {VAT_FRAMES.map((frame) => (
        <span key={frame} aria-hidden className="invisible col-start-1 row-start-1">
          {dipStatus(VAT_DIPS, frame)}
        </span>
      ))}
      <p role="status" aria-live={playing ? "off" : "polite"} className="col-start-1 row-start-1" data-testid="vat-status">
        {text}
      </p>
    </div>
  );
}

export function VatFigureView({ block, number, play, refs = NO_REFS }: { block: IndigoVatBlock; number: number; play: PlayInView; refs?: VatArtRefs }) {
  const shown = vatShown(play.at);
  const leuco = block.forms.find((form) => form.form === "LEUCO");
  const keto = block.forms.find((form) => form.form === "KETO");
  const equation = leuco && keto ? vatEquation({ formula: leuco.compound?.formula ?? null, name: leuco.name }, { formula: keto.compound?.formula ?? null, name: keto.name }) : null;
  const text = vatText(block);
  const dek = text.dek ? <ExplainerSentence sentence={text.dek} /> : undefined;
  return (
    <Figure number={number} kind="diagram" title="One dip, three states" dek={dek} className="kv-vat" id="fig-vat">
      {text.dek ? <SentencesDiffer sentences={[text.dek]} /> : null}
      <div className="grid grid-cols-1 gap-7 rail:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] rail:items-start rail:gap-12" data-testid="vat-figure" data-dip={shown.dip} data-phase={shown.frame} data-plays="view">
        <Frames frames={text.frames} current={shown.frame} dip={shown.dip} dipRef={refs.dipRef} airRef={refs.airRef} onChoose={(frame) => play.choose(vatFrameAt(shown.dip, frame))} />
        <div className="min-w-0">
          <div className="grid justify-items-center gap-3 text-center rail:border-b rail:border-rule rail:pb-5.5 rail:pt-4.5">
            <VatStatus text={dipStatus(shown.dip, shown.frame)} playing={play.playing} />
            <ActionGroup>
              <PlayPauseButton playing={play.playing} motion={play.motion} onToggle={play.toggle} testId="vat-play" />
            </ActionGroup>
          </div>
          {equation ? <VatEquationView equation={equation} leuco={leuco} keto={keto} /> : null}
          <VatFacts block={block} said={text.facts} />
        </div>
      </div>
    </Figure>
  );
}

export function VatFigure({ block, number }: { block: IndigoVatBlock; number: number }) {
  const watched = useRef<HTMLDivElement | null>(null);
  const dipRef = useRef<SVGGElement | null>(null);
  const airRef = useRef<SVGGElement | null>(null);
  const beat = useCallback((at: number) => vatBeat(at, vatTimings(readToken)), []);
  const play = usePlayInView(VAT_BEATS, VAT_REST, watched, beat);
  const frame = vatShown(play.at).frame;
  const moving = play.motion;

  useEffect(() => {
    if (!moving) return;
    if (frame === "in") replay(dipRef.current);
    if (frame === "air") replay(airRef.current);
  }, [frame, moving, play.at]);

  return (
    <div ref={watched} className="min-w-0">
      <VatFigureView block={block} number={number} play={play} refs={{ dipRef, airRef }} />
    </div>
  );
}
