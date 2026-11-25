import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { faceFiles, faceRules, type PageFace } from "../lib/pageFaces";

import { headPreloads } from "./firstScreenFonts";
import { latinFaces } from "./latinFaces";
import { FRONTEND } from "./moduleGraph";

const PHOTOGRAPH = '<link rel="preload" as="image" imageSrcSet="/_next/image?url=%2Fa.jpg&amp;w=960&amp;q=80 960w" imageSizes="100vw" fetchPriority="high"/>';
const FACE = '<link rel="preload" href="/_next/static/media/roman.0a1b2c.woff2" as="font" type="font/woff2" crossorigin="anonymous"/>';
const SCRIPT = '<link rel="preload" as="script" fetchPriority="low" href="/_next/static/chunks/a.js"/>';

const ROMAN: PageFace = {
  family: "Newsreader",
  range: "U+0000-00FF, U+0131",
  src: [{ path: "/_next/static/media/roman.0a1b2c.woff2", weight: "300 600", style: "normal" }],
  fallback: { family: "newsreader Fallback", local: "Times New Roman", ascent: "73.61%", descent: "26.54%", lineGap: "0%", sizeAdjust: "99.84%" }
};

const WEIGHTS: PageFace = {
  family: "IBM Plex Sans",
  range: "U+0020-007E",
  src: [
    { path: "/_next/static/media/medium.3d4e5f.woff2", weight: "500", style: "normal" },
    { path: "/_next/static/media/semibold.6a7b8c.woff2", weight: "600", style: "normal" }
  ],
  fallback: null
};

test("each file of a page-preloaded face is declared at the address it is preloaded from, with its weight, style and range, swapping in", () => {
  const rules = faceRules([ROMAN, WEIGHTS]).split("\n");
  expect(rules).toEqual([
    '@font-face{font-family:"Newsreader";src:url("/_next/static/media/roman.0a1b2c.woff2") format("woff2");font-weight:300 600;font-style:normal;font-display:swap;unicode-range:U+0000-00FF, U+0131}',
    '@font-face{font-family:"newsreader Fallback";src:local("Times New Roman");ascent-override:73.61%;descent-override:26.54%;line-gap-override:0%;size-adjust:99.84%}',
    '@font-face{font-family:"IBM Plex Sans";src:url("/_next/static/media/medium.3d4e5f.woff2") format("woff2");font-weight:500;font-style:normal;font-display:swap;unicode-range:U+0020-007E}',
    '@font-face{font-family:"IBM Plex Sans";src:url("/_next/static/media/semibold.6a7b8c.woff2") format("woff2");font-weight:600;font-style:normal;font-display:swap;unicode-range:U+0020-007E}'
  ]);
  expect(faceFiles([ROMAN, WEIGHTS])).toEqual(["/_next/static/media/roman.0a1b2c.woff2", "/_next/static/media/medium.3d4e5f.woff2", "/_next/static/media/semibold.6a7b8c.woff2"]);
});

test("a face without a measured fallback declares none, and a file named twice is preloaded once", () => {
  expect(faceRules([WEIGHTS])).not.toContain("Fallback");
  expect(faceFiles([WEIGHTS, WEIGHTS])).toEqual(["/_next/static/media/medium.3d4e5f.woff2", "/_next/static/media/semibold.6a7b8c.woff2"]);
});

test("next/font preloads none of the faces it declares, so React writes no face into the head ahead of a masthead photograph", () => {
  const blocks = ["latinFonts.ts", "scriptFonts.ts", "readingScriptFonts.ts"].flatMap((file) => readFileSync(join(FRONTEND, "app", file), "utf8").split(/\nconst /).filter((block) => block.includes("localFont(")));
  expect(blocks).toHaveLength(30);
  expect(blocks.filter((block) => !block.includes("preload: false")).map((block) => /^\w+/.exec(block)?.[0])).toEqual([]);
  expect(latinFaces().filter((face) => face.preloaded).map((face) => face.name)).toEqual(["newsreader", "newsreaderItalic", "plexSans", "plexSansWeights"]);
});

test("a head is read in the order it asks: faces ahead of the masthead photograph are found, and the photograph first is read as first", () => {
  expect(headPreloads(`<html><head>${FACE}${FACE}${PHOTOGRAPH}${SCRIPT}</head><body>${PHOTOGRAPH}</body></html>`)).toEqual(["font", "font", "photograph", "other"]);
  expect(headPreloads(`<html><head>${PHOTOGRAPH}${SCRIPT}${FACE}</head><body>${FACE}</body></html>`)).toEqual(["photograph", "other", "font"]);
  expect(headPreloads(`<html><head>${PHOTOGRAPH.replace(' fetchPriority="high"', "")}${FACE}</head></html>`)).toEqual(["other", "font"]);
});
