import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { FRONTEND } from "./moduleGraph";

const VIEW = readFileSync(join(FRONTEND, "..", "backend", "app", "data", "design", "page-preview-view.html"), "utf8");
const THEME = readFileSync(join(FRONTEND, "app", "tokens.css"), "utf8");
const SCRIPT = /<script>([\s\S]*?)<\/script>/;
const LINE_MOST = 160;
const PHONE = { width: 390, height: 800 };
const DESKTOP = { width: 1280, height: 800 };

const rule = (number: number, verdict: string) => ({ rule: number, title: `Rule ${number} of the checklist`, verdict, evidence: [`evidence for rule ${number}`, "a second line of evidence"] });

const RESULT = {
  subject: { kind: "craft", slug: "Sanganeri-Hand-Block-Printing" },
  pageUrl: "https://kalavigyan.example/crafts/Sanganeri-Hand-Block-Printing",
  previewUrl: "https://kalavigyan.example/preview/abc",
  expiresAt: "2026-11-27T10:00:00Z",
  chapters: ["opening", "chem", "why"],
  components: 19,
  sources: 12,
  parts: [],
  message: "The preview draws the page.",
  report: {
    passed: 19,
    failed: 3,
    judged: 7,
    rules: Array.from({ length: 29 }, (_, at) => rule(at + 1, at < 19 ? "PASS" : at < 22 ? "FAIL" : "JUDGE")),
    sentences: 64,
    fields: [],
    figures: [],
    sourcesByGrade: { A: 4, B: 8 },
    suppliedSources: 0,
    pictures: [],
    picturesByLicence: {},
    message: "19 rules pass, 3 fail and 7 are yours to judge on the private link; fix each failure and preview again.",
    opportunities: [
      {
        shows: "REACTION",
        chapter: "chem",
        what: "the reaction R04, iron and acetic acid to iron(II) acetate and hydrogen, balanced and drawn nowhere",
        facts: ["c9"],
        ways: ["a reaction_player or equation_card you write, its scenes drawn from the figure kit", "compose_component with kind reaction_player, as a shortcut"]
      }
    ],
    bar: {
      barSlug: "Kutch-Ajrakh",
      page: { pictures: 4, figures: 12, interactives: 3, maps: 1 },
      bar: { pictures: 14, figures: 80, interactives: 30, maps: 6 },
      chapters: [{ chapter: "chem", page: { pictures: 1, figures: 6, interactives: 3, maps: 0 }, bar: { pictures: 2, figures: 30, interactives: 20, maps: 0 } }],
      note: "Guidance only."
    }
  }
};

function viewPage(): string {
  const script = SCRIPT.exec(VIEW)?.[1] ?? "";
  const hash = `sha256-${createHash("sha256").update(script, "utf8").digest("base64")}`;
  return VIEW.replace("__KV_THEME__", THEME).replace("__KV_SCRIPT_HASH__", hash);
}

const CRITIQUE = {
  verdict: "The making chapter is a wall of prose.",
  notes: [{ chapter: "made", where: "the eight paragraphs on washing", problem: "A wall of text with no figure beside it.", fix: "Step through the washes with a stage player." }]
};
const READ = {
  state: "READ",
  verdict: "The opening needs its plate.",
  notes: [{ chapter: "opening", where: "the masthead", problem: "No plate beside the lede.", fix: "Set the dye plate beside it." }],
  chapters: ["opening", "made"],
  reason: null,
  provider: "ANTHROPIC",
  model: "claude-opus-5-5",
  costUsd: "0.214000",
  capUsd: "0.50",
  cached: false
};

async function shownCard(page: Page, result: object = RESULT): Promise<void> {
  await page.setContent(viewPage());
  await page.evaluate(() => {
    const sizes: number[] = [];
    Object.assign(window, { kvSizes: sizes });
    window.addEventListener("message", (event) => {
      const message = event.data as { method?: string; params?: { height?: number } } | null;
      if (message?.method === "ui/notifications/size-changed" && typeof message.params?.height === "number") sizes.push(message.params.height);
    });
  });
  await page.evaluate((shown) => window.postMessage({ jsonrpc: "2.0", method: "ui/notifications/tool-result", params: { structuredContent: shown } }, "*"), result);
  await expect(page.locator(".kv-line")).toBeVisible();
}

async function lastHeight(page: Page): Promise<number> {
  await expect.poll(() => page.evaluate(() => (window as unknown as { kvSizes: number[] }).kvSizes.length)).toBeGreaterThan(0);
  return page.evaluate(() => {
    const sizes = (window as unknown as { kvSizes: number[] }).kvSizes;
    return sizes[sizes.length - 1];
  });
}

const toggle = (page: Page) => page.getByRole("button", { name: /Show the full preview|Minimise the preview/ });

test("a preview card starts as one line: its name, its verdict counts, the private link and an expand control", async ({ page }) => {
  await page.setViewportSize(DESKTOP);
  await shownCard(page);
  await expect(page.getByRole("heading", { level: 1, name: "Sanganeri Hand Block Printing" })).toBeVisible();
  await expect(page.locator(".kv-counts")).toHaveText(/19 passed\s*3 failed\s*7 yours to judge/);
  await expect(page.getByRole("link", { name: "Open the private preview" })).toBeVisible();
  await expect(toggle(page)).toHaveAttribute("aria-expanded", "false");
  await expect(toggle(page)).toHaveText("Show the full preview");
  await expect(page.locator("#kv-full")).toBeHidden();
  await expect(page.getByText("The checklist, rule by rule")).toBeHidden();
  await expect(page.getByText("Open the page as it stands")).toBeHidden();
  expect(await lastHeight(page)).toBeLessThanOrEqual(LINE_MOST);
});

test("expanding shows the head and the full report, and collapsing returns the card to its line and its height", async ({ page }) => {
  await page.setViewportSize(DESKTOP);
  await shownCard(page);
  const line = await lastHeight(page);
  await toggle(page).click();
  await expect(toggle(page)).toHaveAttribute("aria-expanded", "true");
  await expect(toggle(page)).toHaveText("Minimise the preview");
  await expect(page.getByText("The checklist, rule by rule")).toBeVisible();
  await expect(page.getByText("Open the page as it stands")).toBeVisible();
  const open = await lastHeight(page);
  expect(open).toBeGreaterThan(line * 4);
  await toggle(page).click();
  await expect(page.locator("#kv-full")).toBeHidden();
  const closed = await lastHeight(page);
  expect(closed).toBeLessThan(open);
  expect(closed).toBe(line);
});

test("the open card lists what the craft's facts could show and sets the page beside Kutch Ajrakh in one quiet line", async ({ page }) => {
  await page.setViewportSize(DESKTOP);
  await shownCard(page);
  await toggle(page).click();
  await expect(page.getByRole("heading", { level: 2, name: "What the facts could show" })).toBeVisible();
  await expect(page.getByText("compose_component with kind reaction_player, as a shortcut")).toBeVisible();
  await expect(page.getByText("Stated by c9")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Beside Kutch Ajrakh" })).toHaveCount(0);
  await expect(page.locator("caption", { hasText: "Kutch Ajrakh" })).toHaveCount(0);
  await expect(page.getByText("For reference, never a target: this page holds 4 pictures, 12 figures, 3 interactives, 1 map; Kutch Ajrakh, the approved page, 14 pictures, 80 figures, 30 interactives, 6 maps.")).toBeVisible();
});

test("without a critique the open card asks for one, and its line counts no design note", async ({ page }) => {
  await page.setViewportSize(DESKTOP);
  await shownCard(page);
  await expect(page.locator(".kv-design-count")).toHaveCount(0);
  await toggle(page).click();
  await expect(page.getByRole("heading", { level: 2, name: "Your design critique" })).toBeVisible();
  await expect(page.getByText("against the designer's rubric (design-critique/1)")).toBeVisible();
  await expect(page.getByRole("heading", { name: "The server's read of the pictures" })).toHaveCount(0);
});

test("the line counts the agent's design notes, and the open card shows its critique and the server's read beside rule 29", async ({ page }) => {
  await page.setViewportSize(DESKTOP);
  await shownCard(page, { ...RESULT, report: { ...RESULT.report, critique: CRITIQUE, designRead: READ } });
  await expect(page.locator(".kv-design-count")).toHaveText("1 design note to judge");
  await expect(page.locator(".kv-counts")).toHaveText(/19 passed\s*3 failed\s*7 yours to judge\s*1 design note to judge/);
  expect(await lastHeight(page)).toBeLessThanOrEqual(LINE_MOST);
  await toggle(page).click();
  const sections = page.locator("section h2");
  const titles = await sections.allTextContents();
  expect(titles.indexOf("Your design critique")).toBe(titles.indexOf("What the facts could show") + 1);
  await expect(page.getByText("The making chapter is a wall of prose.")).toBeVisible();
  await expect(page.getByText("Made: the eight paragraphs on washing")).toBeVisible();
  await expect(page.getByText("What to do: Step through the washes with a stage player.")).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "The server's read of the pictures" })).toBeVisible();
  await expect(page.getByText("Opening: the masthead")).toBeVisible();
  await expect(page.getByText("Read by claude-opus-5-5 for $0.21 of the $0.50 one preview's read may spend.")).toBeVisible();
});

test("a critique with no note says every chapter was read, and the line marks it as passing", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await shownCard(page, { ...RESULT, report: { ...RESULT.report, critique: { verdict: "Set well.", notes: [] } } });
  await expect(page.locator(".kv-design-count")).toHaveText("No design note");
  await expect(page.locator(".kv-design-count.kv-pass")).toHaveCount(1);
  await toggle(page).click();
  await expect(page.getByText("You read every chapter and would change nothing.")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(PHONE.width);
});

test("Escape minimises an open card and leaves the focus on its control", async ({ page }) => {
  await page.setViewportSize(DESKTOP);
  await shownCard(page);
  await toggle(page).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#kv-full")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("#kv-full")).toBeHidden();
  await expect(toggle(page)).toBeFocused();
  await expect(toggle(page)).toHaveAttribute("aria-expanded", "false");
});

test("on a phone the minimised card stays compact and never scrolls sideways", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await shownCard(page);
  expect(await lastHeight(page)).toBeLessThanOrEqual(LINE_MOST + 60);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(PHONE.width);
  await toggle(page).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(PHONE.width);
});
