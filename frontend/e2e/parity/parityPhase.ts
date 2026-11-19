import type { Page } from "@playwright/test";

const PHASE_GRID_PX = 8;

async function shellTop(page: Page): Promise<number> {
  return page.evaluate(() => {
    const shell = document.getElementById("kv-main");
    return shell ? shell.getBoundingClientRect().top + window.scrollY : 0;
  });
}

export function phaseMargin(approvedTop: number, renderedTop: number): number {
  const gap = renderedTop - approvedTop;
  const aligned = Math.ceil(gap / PHASE_GRID_PX) * PHASE_GRID_PX;
  return Math.round((aligned - gap) * 1000) / 1000;
}

export async function alignPhase(approved: Page, rendered: Page): Promise<number> {
  const margin = phaseMargin(await shellTop(approved), await shellTop(rendered));
  if (margin > 0) await rendered.addStyleTag({ content: `#kv-main { margin-block-start: ${margin}px; }` });
  return margin;
}
