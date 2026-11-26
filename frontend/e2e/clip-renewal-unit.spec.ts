import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { clipRenewal, RENEW_AHEAD_MS, RENEW_RETRY_MS, renewalDelay, type RenewalClock } from "@/lib/clipRenewal";
import { clipAddresses, clipEnds, type ClipLink, type HeldClips } from "@/lib/codedClips";
import { codedFrameDocument, filmAskFrom, filmsMessage, FILM_ASK_MESSAGE, FILMS_MESSAGE, type FilmsMessage } from "@/lib/codedFigureFrame";
import { codedFigureShape, codedWords } from "@/lib/componentSpecsScienceCoded";
import type { FrameLook } from "@/lib/sandboxFrame";
import { parseShape } from "@/lib/shape";

const REPO = join(__dirname, "..", "..");
const ORIGIN = "https://kalavigyan.example";
const FIXTURE = JSON.parse(readFileSync(join(REPO, "backend", "app", "data", "kind_fixtures", "coded_figure.json"), "utf8")) as { spec: Record<string, unknown>; units: Record<string, { text: string }> };
const said = (ref: string) => FIXTURE.units[ref]?.text ?? "";
const CLIP = "2d4f6a8c-0e1b-4c3d-9e5f-7a9b1c3d5e7f";
const OBJECT = "https://kv-media.s3.ap-south-1.amazonaws.com/media/craft/eeee/KalaVigyan_Generated-Video_Video_Step-04.mp4";
const signed = (signature: string) => `${OBJECT}?X-Amz-Expires=300&X-Amz-Signature=${signature}`;
const CODE = String(FIXTURE.spec.code).replace("<ul ", '<video data-film="dip" muted></video><video data-film="loop" muted></video><ul ');
const FIGURE = parseShape(codedFigureShape, { ...FIXTURE.spec, code: CODE, films: [{ key: "dip", clip: CLIP }, { key: "loop", src: "/monographs/kit/films/bidri-dip.mp4" }] });
const WORDS = codedWords(FIGURE, said);
const MOVING: FrameLook = { tokens: { "--font-ui": "sans-serif" }, reducedMotion: false };
const START = Date.parse("2026-11-26T10:00:00Z");
const FIVE_MINUTES = 300_000;

const link = (signature: string, end: number): ClipLink => ({ url: signed(signature), expiresAt: new Date(end).toISOString() });

type Timer = { at: number; run: () => void };

function fakeClock(start: number) {
  let now = start;
  let next = 0;
  const timers = new Map<number, Timer>();
  const clock: RenewalClock = {
    now: () => now,
    later: (run, ms) => {
      next += 1;
      timers.set(next, { at: now + ms, run });
      return next;
    },
    cancel: (timer) => timers.delete(timer as number)
  };
  const advance = async (ms: number) => {
    now += ms;
    for (const [id, timer] of [...timers].sort((one, other) => one[1].at - other[1].at)) {
      if (timer.at > now) continue;
      timers.delete(id);
      timer.run();
    }
    await new Promise((settled) => setTimeout(settled, 0));
  };
  return { clock, advance, waits: () => [...timers.values()].map((timer) => timer.at - now) };
}

function renewing(held: HeldClips, answers: (ClipLink | Error)[]) {
  const time = fakeClock(START);
  const asked: string[] = [];
  const posted: FilmsMessage[] = [];
  const read = async (clip: string) => {
    asked.push(clip);
    const answer = answers.shift();
    if (!answer || answer instanceof Error) throw answer ?? new Error("no answer");
    return answer;
  };
  const renewal = clipRenewal(FIGURE, held, { read, post: (message) => posted.push(message), clock: time.clock });
  return { ...time, asked, posted, renewal };
}

test("a clip's address is renewed a minute before it ends and posted to the frame, then renewed again before the new one ends", async () => {
  const first = START + FIVE_MINUTES;
  const second = first + FIVE_MINUTES - 30_000;
  const run = renewing({ dip: link("a", first) }, [link("b", second)]);
  expect(run.waits()).toEqual([FIVE_MINUTES - RENEW_AHEAD_MS]);
  await run.advance(FIVE_MINUTES - RENEW_AHEAD_MS - 1);
  expect(run.asked).toEqual([]);
  await run.advance(1);
  expect(run.asked).toEqual([CLIP]);
  expect(run.posted).toEqual([filmsMessage("dip", signed("b"), second)]);
  expect(run.posted[0][FILMS_MESSAGE]).toEqual({ dip: signed("b") });
  expect(run.waits()).toEqual([second - RENEW_AHEAD_MS - (START + FIVE_MINUTES - RENEW_AHEAD_MS)]);
  expect(renewalDelay(link("c", START + 30_000), START)).toBe(0);
});

test("the frame's ask after the address ended renews it at once, and an ask for a film that is no clip is ignored", async () => {
  const run = renewing({ dip: link("a", START - 1) }, [link("b", START + FIVE_MINUTES)]);
  await run.advance(0);
  expect(run.asked).toEqual([CLIP]);
  run.renewal.ask("loop");
  run.renewal.ask("air");
  await run.advance(0);
  expect(run.asked).toEqual([CLIP]);
  expect(run.posted).toEqual([filmsMessage("dip", signed("b"), START + FIVE_MINUTES)]);
});

test("a renewal that fails is tried again while the address lasts, and after it ends waits for the frame to ask", async () => {
  const run = renewing({ dip: link("a", START + FIVE_MINUTES) }, [new Error("down"), new Error("down"), link("b", START + 2 * FIVE_MINUTES)]);
  await run.advance(FIVE_MINUTES - RENEW_AHEAD_MS);
  expect(run.asked).toHaveLength(1);
  expect(run.waits()).toEqual([RENEW_RETRY_MS]);
  await run.advance(RENEW_AHEAD_MS);
  expect(run.asked).toHaveLength(2);
  expect(run.waits()).toEqual([]);
  expect(run.posted).toEqual([]);
  run.renewal.ask("dip");
  await run.advance(0);
  expect(run.posted).toEqual([filmsMessage("dip", signed("b"), START + 2 * FIVE_MINUTES)]);
});

test("a stopped renewal asks nothing more and posts nothing late", async () => {
  const run = renewing({ dip: link("a", START + FIVE_MINUTES) }, [link("b", START + 2 * FIVE_MINUTES)]);
  run.renewal.ask("dip");
  run.renewal.stop();
  await run.advance(FIVE_MINUTES);
  expect(run.asked).toEqual([CLIP]);
  expect(run.posted).toEqual([]);
  expect(run.waits()).toEqual([]);
});

test("only the frame's own window may ask, and only with a film's key", () => {
  const frame = { name: "frame" };
  expect(filmAskFrom({ source: frame, data: { [FILM_ASK_MESSAGE]: "dip" } }, frame)).toBe("dip");
  expect(filmAskFrom({ source: { name: "other" }, data: { [FILM_ASK_MESSAGE]: "dip" } }, frame)).toBeNull();
  expect(filmAskFrom({ source: frame, data: { [FILM_ASK_MESSAGE]: 3 } }, frame)).toBeNull();
  expect(filmAskFrom({ source: frame, data: { [FILM_ASK_MESSAGE]: "dip", more: 1 } }, frame)).toBeNull();
  expect(filmAskFrom({ source: frame, data: { [FILM_ASK_MESSAGE]: "dip" } }, null)).toBeNull();
});

const LISTENER = `<script>window.heard=[];addEventListener("message",function(event){if(event.data&&typeof event.data==="object"&&${JSON.stringify(FILM_ASK_MESSAGE)} in event.data)window.heard.push(event.data);});</script>`;

async function frameWith(page: Page, end: number) {
  const held = { dip: link("a", end) };
  await page.route("**/*", (route) => route.abort());
  const html = codedFrameDocument({ origin: ORIGIN, figure: FIGURE, words: WORDS, base: null, clips: clipAddresses(held), ends: clipEnds(held) }, MOVING);
  await page.setContent(html.replace("<head>", `<head>${LISTENER}`));
}

const heard = (page: Page) => page.evaluate(() => (window as unknown as { heard: unknown[] }).heard);
const src = (page: Page, key: string) => page.locator(`video[data-film="${key}"]`).getAttribute("src");
const played = (page: Page) =>
  page.evaluate(() => {
    void document.querySelector<HTMLVideoElement>('video[data-film="dip"]')?.play().catch(() => undefined);
  });

test("in the frame a play after the address ended waits, asks the page, and plays the renewed address without a reload", async ({ page }) => {
  await frameWith(page, Date.now() - 1_000);
  expect(await src(page, "dip")).toBe(signed("a"));
  await played(page);
  await expect.poll(() => heard(page)).toContainEqual({ [FILM_ASK_MESSAGE]: "dip" });
  await page.evaluate(() => Object.assign(window, { kept: "the same document" }));
  await page.evaluate((message) => window.postMessage(message, "*"), filmsMessage("dip", signed("b"), Date.now() + FIVE_MINUTES));
  await expect.poll(() => src(page, "dip")).toBe(signed("b"));
  expect(await page.evaluate(() => (window as unknown as { kept?: string }).kept)).toBe("the same document");
  expect(await src(page, "loop")).toBe(`${ORIGIN}/monographs/kit/films/bidri-dip.mp4`);
});

test("in the frame an address that has not ended asks nothing, and a renewal for a film that is no clip changes nothing", async ({ page }) => {
  await frameWith(page, Date.now() + FIVE_MINUTES);
  await played(page);
  await page.waitForTimeout(200);
  expect(await heard(page)).toEqual([]);
  await page.evaluate((message) => window.postMessage(message, "*"), { [FILMS_MESSAGE]: { air: signed("x"), loop: 7 } });
  await page.waitForTimeout(100);
  expect(await src(page, "loop")).toBe(`${ORIGIN}/monographs/kit/films/bidri-dip.mp4`);
  expect(await src(page, "dip")).toBe(signed("a"));
});
