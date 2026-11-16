import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { KNOWN_ANSWER_QUESTIONS, type AnswerRecord } from "./answers";
import { askKnownAnswer } from "./asking";
import { clip } from "./checks";
import type { AnswersReport } from "./report";
import { QUESTIONS_TIMEOUT_MS, SCREENSHOT_DIR, baseUrl, credentials, questionsRequested, runFileName, runId, runStartedAt, writeReport } from "./run";
import { signIn } from "./signIn";
import { installStreamTap } from "./streamTap";

const REPORT_NAME = () => runFileName({ subject: "Known Answers", what: "Report", ext: "json" });

function unaskedProblem(label: string, error: unknown): string {
  const message = error instanceof Error ? (error.message.split("\n")[0] ?? error.message) : String(error);
  return `${label}: could not ask the question: ${clip(message)}`;
}

test("two known-answer questions in Hybrid, in English and Hindi", async ({ page }) => {
  test.skip(!questionsRequested(), "Dispatch with questions=true to ask the known-answer questions.");
  test.setTimeout(QUESTIONS_TIMEOUT_MS);
  await installStreamTap(page);
  const user = await signIn(page, credentials());
  const records: AnswerRecord[] = [];
  const unasked: string[] = [];
  const write = () => {
    const report: AnswersReport = {
      kind: "answers",
      baseUrl: baseUrl(),
      runId: runId(),
      startedAt: runStartedAt(),
      role: user.role,
      problemCount: records.reduce((sum, record) => sum + record.problems.length, 0) + unasked.length,
      unasked,
      questions: records
    };
    writeReport(REPORT_NAME(), report);
  };

  for (const [index, question] of KNOWN_ANSWER_QUESTIONS.entries()) {
    try {
      records.push(await askKnownAnswer(page, question));
    } catch (error) {
      unasked.push(unaskedProblem(question.label, error));
    }
    const shot = runFileName({ subject: `Desktop Question ${question.label}`, what: "Snapshot", ext: "png", sequence: String(index + 1).padStart(2, "0") });
    await page.screenshot({ path: join(SCREENSHOT_DIR, shot), fullPage: true }).catch(() => undefined);
    write();
  }

  const problems = [...unasked, ...records.flatMap((record) => record.problems.map((problem) => `${record.label}: ${problem}`))];
  expect(problems.length, problems.join("\n")).toBe(0);
});
