import { expect, test } from "@playwright/test";

import { ORIGIN, rawLoad } from "./phoneLoadFixture";
import { paintPath, pathLine } from "./phonePath";

const HERO_PATH = "/_next/image?url=%2Fhero.jpg&w=960&q=80";

test("the largest element's path names its picture's request, the render-blocking requests, the fonts and what shared the network with it", () => {
  const path = paintPath(rawLoad());
  expect(path.largestAt).toBe(2900);
  expect(path.firstPaint).toBe(1200);
  expect(path.navigation).toEqual({ firstByte: 562, end: 791 });
  expect(path.picture).toEqual({ url: HERO_PATH, kind: "img", priority: "High", start: 700, firstByte: 1260, end: 2800, bytes: 120 * 1024 });
  expect(path.blocking).toEqual([{ url: "/monographs/kit/monograph.css", kind: "link", priority: "VeryHigh", start: 620, firstByte: 1180, end: 1500, bytes: 70 * 1024 }]);
  expect(path.fonts.map((font) => [font.url, font.priority])).toEqual([["/_next/static/media/newsreader.woff2", "unknown"]]);
  expect(path.sharing.map((request) => request.url)).toEqual(["/_next/static/chunks/a.js", "/monographs/kit/monograph.css", "/_next/static/media/newsreader.woff2"]);
  expect(path.sharedCount).toBe(3);
  expect(path.sharedBytes).toBe(295 * 1024);
});

test("the main thread's work before the largest paint counts each long task up to the paint and names the scripts that ran", () => {
  const path = paintPath({ ...rawLoad(), tasks: [{ at: 1000, duration: 400 }, { at: 2800, duration: 300 }, { at: 3000, duration: 500 }] });
  expect(path.tasksBefore).toBe(500);
  expect(path.scriptsBefore).toEqual([{ url: `${ORIGIN}/_next/static/chunks/a.js`, duration: 90, at: 1010 }]);
  expect(paintPath(rawLoad()).tasksBefore).toBe(520);
});

test("a largest element that is text waits on no request of its own, and a load with no largest paint cannot be traced", () => {
  const text = paintPath({ ...rawLoad(), paints: [{ at: 1300, node: "h1.kv-q", url: "" }] });
  expect(text.picture).toBeNull();
  expect(text.sharedCount).toBe(0);
  expect(text.blocking.map((request) => request.url)).toEqual(["/monographs/kit/monograph.css"]);
  expect(pathLine(text)).toContain("it waits on no request of its own");
  expect(() => paintPath({ ...rawLoad(), paints: [] })).toThrow("painted no largest element");
});

test("the path reads as one line for the log", () => {
  expect(pathLine(paintPath(rawLoad()))).toBe(
    `largest element img (${HERO_PATH}) at 2900 ms: document first byte at 562, done at 791; render-blocking requests 1 (70.0 KB) done at 1500; fonts 1 (25.0 KB) done at 1900; first paint at 1200; its picture ${HERO_PATH} (High) requested at 700, first byte at 1260, done at 2800; requests sharing the network with it 3 (295.0 KB); long tasks before it 520 ms (/_next/static/chunks/a.js 90 ms)`
  );
});
