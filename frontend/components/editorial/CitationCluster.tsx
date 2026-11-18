"use client";

import { useCallback, useEffect, useId, useRef, useState, type RefObject } from "react";

import { SourcePanel } from "@/components/editorial/SourcePanel";
import { playMotion } from "@/components/motion/useNamedMotion";
import { AnchoredPopover } from "@/components/ui/AnchoredPopover";
import { Sheet } from "@/components/ui/Sheet";
import { MODAL_LAYER_SELECTOR } from "@/lib/focusable";
import { citationCluster, citationSurface, type CitationSurface, type EvidenceState } from "@/lib/citationCluster";
import type { Citation, SourceRef } from "@/lib/types";

export const SENTENCE_HOST = '[data-cite-host], [data-testid="answer-sentence"]';
export const MARGIN_DOCK = "[data-margin-rail]";
const WORD_JOINER = "⁠";

export type CiteProps = {
  citations: readonly Citation[];
  numbers: ReadonlyMap<string, number>;
  sourcesById: ReadonlyMap<string, SourceRef>;
  norm?: EvidenceState;
  borrowed?: ReadonlyMap<string, string>;
};

function surfaceFor(button: HTMLElement): { surface: CitationSurface; dock: HTMLElement | null } {
  const dock = button.closest("[data-spread]")?.querySelector<HTMLElement>(MARGIN_DOCK) ?? null;
  const shown = dock !== null && dock.getBoundingClientRect().width > 0;
  return { surface: citationSurface(window.innerWidth, shown), dock: shown ? dock : null };
}

function useLitSentence(button: RefObject<HTMLElement | null>, lit: boolean) {
  useEffect(() => {
    const host = button.current?.closest(SENTENCE_HOST);
    if (!host || !lit) return;
    host.setAttribute("data-lit", "");
    return () => host.removeAttribute("data-lit");
  }, [button, lit]);
}

export function Cite({ citations, numbers, sourcesById, norm, borrowed }: CiteProps) {
  const view = citationCluster(citations, numbers, sourcesById);
  const id = useId();
  const panelId = `${id}-sources`;
  const headingId = `${id}-heading`;
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const dockRef = useRef<HTMLElement | null>(null);
  const [surface, setSurface] = useState<CitationSurface | null>(null);
  const [stacked, setStacked] = useState(false);
  useLitSentence(buttonRef, surface !== null);

  const close = useCallback(() => setSurface(null), []);
  const closeAndReturn = useCallback(() => {
    setSurface(null);
    buttonRef.current?.focus({ preventScroll: true });
  }, []);

  useEffect(() => {
    if (surface === null || surface === "sheet") return;
    const frame = requestAnimationFrame(() => closeRef.current?.focus({ preventScroll: true }));
    return () => cancelAnimationFrame(frame);
  }, [surface]);

  if (view.entries.length === 0) return null;

  function toggle() {
    const button = buttonRef.current;
    if (!button) return;
    if (surface !== null) {
      close();
      return;
    }
    playMotion(button);
    const placed = surfaceFor(button);
    dockRef.current = placed.dock;
    setStacked(button.closest(MODAL_LAYER_SELECTOR) !== null);
    setSurface(placed.surface);
  }

  const panel = <SourcePanel entries={view.entries} headingId={headingId} onClose={closeAndReturn} closeRef={closeRef} norm={norm} borrowed={borrowed} />;

  return (
    <span className="kv-nowrap kv-cite-cluster" data-testid="citation-cluster">
      {WORD_JOINER}
      <button
        ref={buttonRef}
        type="button"
        className="kv-cite motion-press"
        aria-haspopup="dialog"
        aria-controls={surface === null ? undefined : panelId}
        aria-expanded={surface !== null}
        aria-label={view.name}
        aria-describedby={view.description ? `${id}-titles` : undefined}
        data-testid="citation-chip"
        data-numbers={view.label}
        onClick={toggle}
      >
        {view.label}
      </button>
      {view.description ? (
        <span id={`${id}-titles`} hidden>
          {view.description}
        </span>
      ) : null}
      <Sheet open={surface === "sheet"} onClose={close} labelledBy={headingId} panelId={panelId} stacked={stacked}>
        {panel}
      </Sheet>
      <AnchoredPopover
        open={surface === "popover" || surface === "margin"}
        onClose={close}
        anchorRef={buttonRef}
        label={view.name}
        labelledBy={headingId}
        panelId={panelId}
        dockRef={surface === "margin" ? dockRef : undefined}
        maxWidth={380}
        className="w-[min(380px,calc(100vw-32px))] px-[1.125rem] pt-4 pb-3.5"
      >
        {panel}
      </AnchoredPopover>
    </span>
  );
}
