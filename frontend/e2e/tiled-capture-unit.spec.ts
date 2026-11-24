import { expect, test } from "@playwright/test";
import sharp from "sharp";

import { pixelDifference } from "./parity/parityMeasure";
import { placedTile, roomBelow, stitched, tileClip, tiledCapture, tileHeight, tilePlan, type Placed } from "./tiledCapture";

const LINES = Array.from({ length: 40 }, (_, at) => `<p style="margin:0;font:13px/17px serif">Line ${at + 1}: iron printed on tannin turns chocolate-black.</p>`).join("");

const TALL = `<!doctype html><html><body style="margin:0">
<div style="height:1000.3px"></div>
<figure id="tall" style="margin:0 0 0 8px;width:304px;height:704px;overflow:hidden;background:repeating-linear-gradient(rgb(200,0,0) 0 3px,rgb(0,0,160) 3px 7.5px)">${LINES}</figure>
<div style="height:3000px"></div>
</body></html>`;

const LAST = `<!doctype html><html><body style="margin:0">
<div style="height:1000px"></div>
<figure id="last" style="margin:0;height:200px;background:rgb(0,160,0)"></figure>
</body></html>`;

const FROZEN = `<!doctype html><html><body style="margin:0">
<script>window.requestAnimationFrame = () => 0;</script>
<figure id="tall" style="margin:0;height:200px;background:rgb(0,160,0)"></figure>
</body></html>`;

const RESTLESS = `<!doctype html><html><body style="margin:0">
<figure id="tall" style="margin:0;height:100px;background:rgb(0,160,0)"></figure>
<script>
let odd = false;
const grow = () => { odd = !odd; document.getElementById("tall").style.height = odd ? "101px" : "100px"; requestAnimationFrame(grow); };
requestAnimationFrame(grow);
</script>
</body></html>`;

const CAPTURE = { style: "", timeout: 5000 };

test.use({ viewport: { width: 360, height: 296 }, deviceScaleFactor: 2.625 });

function placedTop(placed: Placed): number {
  if (placed.state !== "still") throw new Error(`the view was not placed: ${placed.state}`);
  return placed.box.y;
}

async function solid(width: number, height: number, colour: { r: number; g: number; b: number }): Promise<Buffer> {
  return sharp({ create: { width, height, channels: 4, background: { ...colour, alpha: 1 } } })
    .png()
    .toBuffer();
}

test("a tile is the screen's height less one grid step, floored to the 8-pixel grid on which every tested scale draws whole device pixels", () => {
  expect(tileHeight(800)).toBe(792);
  expect(tileHeight(900)).toBe(888);
  expect(tileHeight(1194)).toBe(1184);
  expect(tileHeight(300)).toBe(288);
  expect(tileHeight(10)).toBe(8);
});

test("a view is cut into tiles from its top, the last one holding what is left", () => {
  expect(tilePlan(704, 288)).toEqual([
    { from: 0, height: 288 },
    { from: 288, height: 288 },
    { from: 576, height: 128 }
  ]);
  expect(tilePlan(288, 288)).toEqual([{ from: 0, height: 288 }]);
  expect(tilePlan(100.5, 792)).toEqual([{ from: 0, height: 100.5 }]);
});

test("a tile's clip spans the view's whole pixels across and starts where the tile lies on the screen", () => {
  expect(tileClip({ x: 8.4, y: -287.75, width: 304, height: 704 }, { from: 288, height: 288 })).toEqual({ x: 8, y: 0.25, width: 305, height: 288 });
  expect(tileClip({ x: 8, y: -576, width: 304, height: 704 }, { from: 576, height: 127.5 })).toEqual({ x: 8, y: 0, width: 304, height: 128 });
});

test("tiles are stitched top to bottom into one picture, and a single tile is the picture", async () => {
  const red = await solid(4, 3, { r: 200, g: 0, b: 0 });
  const blue = await solid(4, 2, { r: 0, g: 0, b: 160 });
  expect(await stitched([red])).toBe(red);
  const { data, info } = await sharp(await stitched([red, blue]))
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  expect([info.width, info.height]).toEqual([4, 5]);
  const rows = Array.from({ length: 5 }, (_, row) => [...data.subarray(row * 12, row * 12 + 3)]);
  expect(rows).toEqual([[200, 0, 0], [200, 0, 0], [200, 0, 0], [0, 0, 160], [0, 0, 160]]);
});

test("a view taller than the screen is captured the same, pixel for pixel, wherever the page was scrolled before", async ({ page }) => {
  await page.setContent(TALL);
  const captures: Buffer[] = [];
  for (const start of [0, 1234.57, 4000]) {
    await page.evaluate((top) => window.scrollTo({ top, behavior: "instant" }), start);
    const capture = await tiledCapture(page, "#tall", CAPTURE);
    if (typeof capture === "string") throw new Error(`the view was not captured: ${capture}`);
    captures.push(capture);
  }
  expect(await sharp(captures[0]).metadata()).toMatchObject({ width: 798, height: 1848 });
  for (const capture of captures.slice(1)) expect((await pixelDifference(captures[0], capture)).ratio).toBe(0);
});

test("a view at the end of the page is placed at the top of the screen once the page has room below it", async ({ page }) => {
  await page.setContent(LAST);
  const clamped = placedTop(await placedTile(page, "#last", 0));
  await roomBelow(page);
  expect(clamped).toBeCloseTo(96, 0);
  expect(placedTop(await placedTile(page, "#last", 0))).toBeCloseTo(0, 0);
});

test("a page that draws no frames is named as stalled within seconds, not after the capture's timeout", async ({ page }) => {
  await page.setContent(FROZEN);
  const started = Date.now();
  expect(await tiledCapture(page, "#tall", CAPTURE)).toBe("stalled");
  expect(Date.now() - started).toBeLessThan(CAPTURE.timeout);
});

test("a view whose box changes every frame is named as moving, and an absent view as missing", async ({ page }) => {
  await page.setContent(RESTLESS);
  expect(await tiledCapture(page, "#tall", CAPTURE)).toBe("moving");
  expect(await tiledCapture(page, "#absent", CAPTURE)).toBe("missing");
});
