"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { motionAllowedNow } from "@/components/motion/useMotionAllowed";
import { Button } from "@/components/ui/button";
import type { KitMotion } from "@/lib/artKit";
import { kitSchedule, kitStatus, kitStillStep, kitTimings } from "@/lib/artKitMotion";

type PlayProps = { figureId: string; labels: string[]; motions: (KitMotion | null)[] };

function readToken(token: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(token);
}

function replay(element: Element): void {
  element.removeAttribute("data-playing");
  element.getBoundingClientRect();
  element.setAttribute("data-playing", "");
  element.addEventListener("animationend", () => element.removeAttribute("data-playing"), { once: true });
}

function mark(figure: HTMLElement | null, panel: number | null): void {
  figure?.querySelectorAll("[data-kit-panel]").forEach((node) => {
    if (Number(node.getAttribute("data-kit-panel")) === panel) node.setAttribute("aria-current", "step");
    else node.removeAttribute("aria-current");
  });
}

export function KitPlay({ figureId, labels, motions }: PlayProps) {
  const [status, setStatus] = useState("");
  const [playing, setPlaying] = useState(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const shown = useRef<number | null>(null);

  const stop = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  useEffect(() => stop, [stop]);

  const show = useCallback(
    (panel: number | null, moves: boolean) => {
      const figure = document.getElementById(figureId);
      shown.current = panel;
      mark(figure, panel);
      if (moves && panel !== null) figure?.querySelectorAll(`[data-kit-move="${panel}"]`).forEach(replay);
      setStatus(kitStatus(panel, labels));
    },
    [figureId, labels]
  );

  const play = useCallback(() => {
    stop();
    if (!motionAllowedNow()) {
      show(kitStillStep(shown.current, labels.length), false);
      return;
    }
    setPlaying(true);
    for (const beat of kitSchedule(motions, kitTimings(readToken))) {
      timers.current.push(
        setTimeout(() => {
          show(beat.panel, beat.moves);
          if (beat.panel === null) setPlaying(false);
        }, beat.at)
      );
    }
  }, [labels.length, motions, show, stop]);

  return (
    <div className="kv-kit-play">
      <Button variant="quiet" size="sm" aria-pressed={playing} onClick={play}>
        Play
      </Button>
      <p className="kv-kit-status" role="status" aria-live="polite">
        {status}
      </p>
    </div>
  );
}
