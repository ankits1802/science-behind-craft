import { appendFileSync, existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import type { RunReport } from "./report";
import { REPORT_DIR, questionsRequested, runFileName, runId, runStartedAt, writeRunFile } from "./run";
import { summaryMarkdown } from "./summaryMarkdown";

function readReports(): RunReport[] {
  if (!existsSync(REPORT_DIR)) return [];
  return readdirSync(REPORT_DIR)
    .filter((name) => name.endsWith(".json"))
    .sort()
    .map((name) => JSON.parse(readFileSync(join(REPORT_DIR, name), "utf8")) as RunReport);
}

export default async function globalTeardown(): Promise<void> {
  const markdown = summaryMarkdown(readReports(), {
    runId: runId(),
    baseUrl: process.env.E2E_BASE_URL ?? null,
    startedAt: runStartedAt(),
    questionsRequested: questionsRequested()
  });
  writeRunFile(join(REPORT_DIR, runFileName({ subject: "Summary", what: "Report", ext: "md" })), markdown);
  const stepSummary = process.env.GITHUB_STEP_SUMMARY;
  if (stepSummary) appendFileSync(stepSummary, markdown, "utf8");
}
