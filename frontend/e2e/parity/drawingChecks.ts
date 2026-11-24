import { readFileSync } from "node:fs";
import { join } from "node:path";

import type { ElementHandle, Page } from "@playwright/test";

export type DrawnComponent = { label: string; role: string; placed: boolean };
export type DrawingPlan = { components: DrawnComponent[]; masthead: string | null; chapters: string[] };
export type DrawnProblem = { label: string; problem: string };
export type DrawingReview = { problems: DrawnProblem[]; chapters: { key: string; top: number; height: number }[]; height: number };
export type DrawingLimits = { iconView: number; iconLeast: number; iconWidth: number; figureText: number; svgText: number };

type DrawingKit = {
  limits: DrawingLimits;
  componentProblems: (element: Element) => string[];
  review: (plan: DrawingPlan) => DrawingReview;
  settle: (most: number) => Promise<number>;
};

export const DRAWING_CHECKS_PATH = join(__dirname, "..", "..", "..", "backend", "app", "data", "design", "drawing-checks.js");
const SOURCE = readFileSync(DRAWING_CHECKS_PATH, "utf8");

export async function installDrawingChecks(page: Page): Promise<void> {
  await page.evaluate(SOURCE);
}

export async function drawingProblems(page: Page, root: ElementHandle<Element>): Promise<string[]> {
  await installDrawingChecks(page);
  return root.evaluate((element) => (globalThis as unknown as { kvDrawing: DrawingKit }).kvDrawing.componentProblems(element));
}

export async function drawingReview(page: Page, plan: DrawingPlan): Promise<DrawingReview> {
  await installDrawingChecks(page);
  return page.evaluate((given) => (globalThis as unknown as { kvDrawing: DrawingKit }).kvDrawing.review(given), plan);
}

export async function drawingLimits(page: Page): Promise<DrawingLimits> {
  await installDrawingChecks(page);
  return page.evaluate(() => ({ ...(globalThis as unknown as { kvDrawing: DrawingKit }).kvDrawing.limits }));
}
