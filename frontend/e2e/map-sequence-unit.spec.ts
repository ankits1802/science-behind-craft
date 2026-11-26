import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { MapSequence } from "@/components/monograph/kinds/general/MapSequence";
import { sequenceRest } from "@/components/monograph/kinds/general/useMapSequence";
import type { MapStepSpec } from "@/lib/componentSpecsMapLayer";
import { isPlaying, played, restingPlay, type PlayAction } from "@/lib/playInView";

import { attribute } from "./explainerRender";
import { FRONTEND, moduleFile, staticImports } from "./moduleGraph";

const STEPS: MapStepSpec[] = [
  { text: "u0011", places: [0], routes: [], rings: [], districts: false },
  { text: "u0012", places: [1], routes: [0], rings: [], districts: false },
  { text: "u0013", places: [2], routes: [], rings: [0], districts: false },
  { text: "u0014", places: [3], routes: [], rings: [], districts: true }
];
const SEEN: PlayAction = { type: "seen", on: true, motion: true };
const TICK: PlayAction = { type: "tick", count: STEPS.length };

function drawn(at: number, playing: boolean): string {
  return renderToStaticMarkup(createElement(MapSequence, { steps: STEPS, play: { at, playing, choose: () => undefined, toggle: () => undefined }, renderUnit: (ref: string) => ref }));
}

function playButton(html: string): string {
  return /<button[^>]*data-testid="map-sequence-play"[^>]*>[\s\S]*?<\/button>/.exec(html)?.[0] ?? "";
}

test("a map's sequence rests on its last step, with one Play and the step it shows named", () => {
  const html = drawn(sequenceRest(STEPS.length), false);
  expect(sequenceRest(STEPS.length)).toBe(3);
  expect(sequenceRest(0)).toBe(0);
  expect(attribute(html, "map-step", "aria-pressed")).toEqual(["false", "false", "false", "true"]);
  expect(playButton(html)).toContain("<span>Play</span>");
  expect(html).toMatch(/role="status" aria-live="polite" data-testid="map-sequence-status">Step 4 of 4</);
  expect(attribute(html, "map-sequence", "data-plays")).toEqual(["view"]);
});

test("playing, the sequence reads Pause and says nothing while its steps move", () => {
  const html = drawn(1, true);
  expect(attribute(html, "map-step", "aria-pressed")).toEqual(["false", "true", "false", "false"]);
  expect(playButton(html)).toContain("<span>Pause</span>");
  expect(attribute(html, "map-sequence-status", "aria-live")).toEqual(["off"]);
});

test("in view with motion allowed the sequence plays from its first step and loops, where it once stopped on its last", () => {
  const start = played(played(restingPlay(sequenceRest(STEPS.length)), SEEN), { type: "start" });
  expect([start.at, isPlaying(start, STEPS.length)]).toEqual([0, true]);
  const stops: number[] = [];
  let state = start;
  for (let tick = 0; tick < STEPS.length; tick += 1) {
    state = played(state, TICK);
    stops.push(state.at);
  }
  expect(stops).toEqual([1, 2, 3, 0]);
  expect(isPlaying(state, STEPS.length)).toBe(true);
  const pressed = played(start, { type: "choose", at: 2 });
  expect([pressed.at, isPlaying(pressed, STEPS.length)]).toEqual([2, true]);
  const out = played(start, { type: "seen", on: false, motion: true });
  expect(isPlaying(out, STEPS.length)).toBe(false);
});

test("under either reduced-motion switch the sequence never plays, and Play shows the next step at once", () => {
  const still = played(restingPlay(sequenceRest(STEPS.length)), { type: "seen", on: true, motion: false });
  expect(isPlaying(still, STEPS.length)).toBe(false);
  expect(played(still, { type: "toggle", motion: false, count: STEPS.length }).at).toBe(0);
  expect(played({ ...still, at: 1 }, { type: "toggle", motion: false, count: STEPS.length }).at).toBe(2);
});

test("the sequence's hook is the shared play-in-view, and the old playback reducer is gone", () => {
  const hook = readFileSync(moduleFile("@/components/monograph/kinds/general/useMapSequence"), "utf8");
  expect(staticImports(hook)).toContain("@/components/motion/usePlayInView");
  expect(existsSync(join(FRONTEND, "components", "answer", "matter", "usePlayback.ts"))).toBe(false);
  expect(readFileSync(join(FRONTEND, "lib", "reactionPlayer.ts"), "utf8")).not.toContain("playbackStep");
});
