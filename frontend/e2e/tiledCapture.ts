import type { Page } from "@playwright/test";
import sharp from "sharp";

import { PHASE_GRID_PX } from "./parity/parityPhase";

export type Box = { x: number; y: number; width: number; height: number };
export type Tile = { from: number; height: number };
export type Unplaced = "missing" | "stalled" | "moving";
export type Placed = { state: "still"; box: Box } | { state: Unplaced };
export type Capture = Buffer | Unplaced;
export type CaptureOptions = { style: string; timeout: number };

export const FRAME_WAIT_MS = 2000;
export const STILL_FRAMES_MOST = 60;
export const ROOM_BELOW = "body { padding-block-end: 100vh !important; }";

const EDGE = 1e-3;

export function tileHeight(viewportHeight: number): number {
  return Math.max(PHASE_GRID_PX, Math.floor((viewportHeight - PHASE_GRID_PX) / PHASE_GRID_PX) * PHASE_GRID_PX);
}

export function tilePlan(height: number, tile: number): Tile[] {
  const count = Math.max(1, Math.ceil(height / tile - EDGE));
  return Array.from({ length: count }, (_, index) => ({ from: index * tile, height: Math.min(tile, height - index * tile) }));
}

export function tileClip(box: Box, tile: Tile): Box {
  const left = Math.floor(box.x + EDGE);
  return { x: left, y: box.y + tile.from, width: Math.ceil(box.x + box.width - EDGE) - left, height: Math.ceil(tile.height - EDGE) };
}

export async function stitched(parts: readonly Buffer[]): Promise<Buffer> {
  if (parts.length === 1) return parts[0];
  const sizes = await Promise.all(parts.map((part) => sharp(part).metadata()));
  const tops = sizes.map((_, at) => sizes.slice(0, at).reduce((sum, size) => sum + size.height, 0));
  const height = tops[tops.length - 1] + sizes[sizes.length - 1].height;
  const width = Math.max(...sizes.map((size) => size.width));
  const canvas = sharp({ create: { width, height, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } });
  return canvas
    .composite(parts.map((input, at) => ({ input, top: tops[at], left: 0 })))
    .png()
    .toBuffer();
}

export async function roomBelow(page: Page): Promise<void> {
  await page.addStyleTag({ content: ROOM_BELOW });
}

export async function framesDrawn(page: Page): Promise<boolean> {
  return page.evaluate(
    (wait) =>
      new Promise<boolean>((resolve) => {
        const timer = setTimeout(() => resolve(false), wait);
        requestAnimationFrame(() => {
          clearTimeout(timer);
          resolve(true);
        });
      }),
    FRAME_WAIT_MS
  );
}

export async function placedTile(page: Page, selector: string, from: number): Promise<Placed> {
  return page.evaluate(
    async ({ target, offset, wait, most }): Promise<Placed> => {
      const element = document.querySelector(target);
      if (!element) return { state: "missing" };
      const place = () => window.scrollTo({ top: element.getBoundingClientRect().top + window.scrollY + offset, behavior: "instant" });
      const pause = () => new Promise((resolve) => setTimeout(resolve, wait));
      const frame = () => Promise.race([new Promise<boolean>((resolve) => requestAnimationFrame(() => resolve(true))), pause().then(() => false)]);
      place();
      const pictures = [...element.querySelectorAll("img")].map((image) => image.decode().catch(() => undefined));
      await Promise.race([Promise.all([document.fonts.ready, ...pictures]), pause()]);
      let last = "";
      for (let count = 0; count < most; count += 1) {
        place();
        if (!(await frame())) return { state: "stalled" };
        const rect = element.getBoundingClientRect();
        const box = { x: rect.left, y: rect.top, width: rect.width, height: rect.height };
        if (JSON.stringify(box) === last) return box.width > 0 && box.height > 0 ? { state: "still", box } : { state: "missing" };
        last = JSON.stringify(box);
      }
      return { state: "moving" };
    },
    { target: selector, offset: from, wait: FRAME_WAIT_MS, most: STILL_FRAMES_MOST }
  );
}

export async function tiledCapture(page: Page, selector: string, options: CaptureOptions): Promise<Capture> {
  const viewport = page.viewportSize();
  if (!viewport) return "missing";
  const first = await placedTile(page, selector, 0);
  if (first.state !== "still") return first.state;
  const parts: Buffer[] = [];
  for (const tile of tilePlan(first.box.height, tileHeight(viewport.height))) {
    const placed = tile.from === 0 ? first : await placedTile(page, selector, tile.from);
    if (placed.state !== "still") return placed.state;
    const shot = { clip: tileClip(placed.box, tile), animations: "disabled" as const, style: options.style, timeout: options.timeout };
    const image = await page.screenshot(shot).catch(() => null);
    if (!image) return "missing";
    parts.push(image);
  }
  return stitched(parts);
}
