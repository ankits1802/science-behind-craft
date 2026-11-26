"use client";

import { useCallback, useEffect, useLayoutEffect, useRef } from "react";

import { motionAllowedNow } from "@/components/motion/useMotionAllowed";
import { usePlayInView } from "@/components/motion/usePlayInView";
import { PlayPauseButton } from "@/components/ui/PlayPauseButton";
import type { KitMotion } from "@/lib/artKit";
import { kitBeat, kitPanel, kitStatus, kitTimings } from "@/lib/artKitMotion";

export type KitPlayProps = { figureId: string; labels: string[]; motions: (KitMotion | null)[] };

function readToken(token: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(token);
}

function replay(element: Element): void {
  if (!motionAllowedNow()) return;
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

export function KitPlay({ figureId, labels, motions }: KitPlayProps) {
  const watched = useRef<Element | null>(null);
  const rest = labels.length;
  const beat = useCallback((at: number) => kitBeat(motions, at, kitTimings(readToken)), [motions]);
  const play = usePlayInView(rest + 1, rest, watched, beat);
  const panel = kitPanel(play.at, rest);
  const moving = play.motion;

  useLayoutEffect(() => {
    watched.current = document.getElementById(figureId);
  }, [figureId]);

  useEffect(() => {
    const figure = document.getElementById(figureId);
    mark(figure, panel);
    if (panel !== null && moving && motions[panel] !== null) figure?.querySelectorAll(`[data-kit-move="${panel}"]`).forEach(replay);
  }, [figureId, panel, moving, motions]);

  return (
    <div className="kv-kit-play" data-testid="kit-play" data-at={play.at}>
      <PlayPauseButton playing={play.playing} motion={play.motion} onToggle={play.toggle} testId="kit-play-button" />
      <p className="kv-kit-status" role="status" aria-live={play.playing ? "off" : "polite"}>
        {moving || play.at !== rest ? kitStatus(panel, labels) : ""}
      </p>
    </div>
  );
}
