import { expect, type Page } from "@playwright/test";

import {
  ANSWER_DEADLINE_MS,
  EXPECTED_DEPTH_LABEL,
  STALL_LIMIT_MS,
  answerProblems,
  answerRecord,
  type AnswerRecord,
  type KnownAnswerQuestion,
  type WaitOutcome
} from "./answers";
import { CRAFT_SLUG } from "./run";
import { settle } from "./screenRun";
import { glanceAtTaps, pageNow, readTaps } from "./streamTap";

const POLL_MS = 2_000;
const LAST_STREAM_GRACE_MS = 1_500;
const UI_SETTLE_MS = 30_000;
const AUTO_LANGUAGE = /^Auto\b/;

async function chooseAutoLanguage(page: Page): Promise<void> {
  const picker = page.getByRole("button", { name: "Answer language", exact: true });
  if ((await picker.count()) === 0 || AUTO_LANGUAGE.test((await picker.innerText()).trim())) return;
  await picker.click();
  await page.getByRole("option", { name: AUTO_LANGUAGE }).click();
  await expect(picker).toHaveText(AUTO_LANGUAGE);
}

async function chooseDepth(page: Page): Promise<void> {
  const depth = page.getByRole("group", { name: "Depth" }).getByRole("button", { name: EXPECTED_DEPTH_LABEL, exact: true });
  if ((await depth.getAttribute("aria-pressed")) !== "true") await depth.click();
  await expect(depth).toHaveAttribute("aria-pressed", "true");
}

async function waitForStreamEnd(page: Page, clickedAt: number): Promise<WaitOutcome | null> {
  for (;;) {
    await page.waitForTimeout(POLL_MS);
    const glance = await glanceAtTaps(page, clickedAt);
    if (glance.endedAt !== null) {
      await page.waitForTimeout(LAST_STREAM_GRACE_MS);
      const again = await glanceAtTaps(page, clickedAt);
      if (again.streams === glance.streams && again.endedAt !== null) return null;
      continue;
    }
    if (glance.now - clickedAt > ANSWER_DEADLINE_MS) return "timeout";
    if (glance.lastActivity === null && glance.now - clickedAt > STALL_LIMIT_MS) return "never-started";
    if (glance.lastActivity !== null && glance.now - glance.lastActivity > STALL_LIMIT_MS) return "stalled";
  }
}

async function readPageSentences(page: Page, record: AnswerRecord): Promise<void> {
  const settled = await expect(page.getByTestId("answer-progress"))
    .toHaveCount(0, { timeout: UI_SETTLE_MS })
    .then(() => true)
    .catch(() => false);
  if (!settled) record.problems.push("the page still shows progress after the stream ended");
  const chips = await page
    .getByTestId("answer-view")
    .getByTestId("answer-sentence")
    .evaluateAll((nodes) => nodes.map((node) => node.querySelectorAll('[data-testid="citation-chip"]').length));
  record.pageSentences = chips.length;
  record.pageSentencesWithoutChip = chips.filter((count) => count === 0).length;
}

export async function askKnownAnswer(page: Page, question: KnownAnswerQuestion): Promise<AnswerRecord> {
  await page.goto(`/ask?craft=${encodeURIComponent(CRAFT_SLUG)}`, { waitUntil: "domcontentloaded" });
  await settle(page);
  await chooseDepth(page);
  await chooseAutoLanguage(page);
  await page.getByLabel("Your question").fill(question.question);
  const clickedAt = await pageNow(page);
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  const waited = await waitForStreamEnd(page, clickedAt);
  const streams = await readTaps(page, clickedAt);
  const record = answerRecord({ question, stream: streams.at(-1) ?? null, streamsOpened: streams.length, clickedAt, waited });
  if (!waited) await readPageSentences(page, record);
  record.problems.push(...answerProblems(record, question));
  return record;
}
