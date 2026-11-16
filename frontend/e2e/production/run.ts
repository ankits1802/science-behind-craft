import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

import { fileName } from "@/lib/naming";

export const REPORT_DIR = process.env.E2E_REPORT_DIR || "production-run";
export const SCREENSHOT_DIR = join(REPORT_DIR, "screens");
export const REPORT_ENTITY = "Eval-Run";
export const CRAFT_SLUG = "Kutch-Ajrakh";
export const NOT_FOUND_PATH = "/no-such-page-e2e";
export const SCREENS_TIMEOUT_MS = 10 * 60_000;
export const QUESTIONS_TIMEOUT_MS = 25 * 60_000;

const STARTED_HERE = new Date().toISOString();

export type Credentials = { email: string; password: string };

export type RunFile = { subject: string; what: string; ext: string; sequence?: string };

export function runId(): string | null {
  return process.env.E2E_RUN_ID || null;
}

export function runStartedAt(): string {
  return process.env.E2E_RUN_STARTED_AT || STARTED_HERE;
}

export function baseUrl(): string {
  const url = process.env.E2E_BASE_URL;
  if (!url) throw new Error("Set E2E_BASE_URL to the site under test.");
  return url;
}

export function questionsRequested(): boolean {
  return process.env.E2E_QUESTIONS === "1";
}

export function credentials(): Credentials {
  const email = process.env.E2E_EMAIL ?? "";
  const password = process.env.E2E_PASSWORD ?? "";
  const missing = [email ? null : "E2E_EMAIL", password ? null : "E2E_PASSWORD"].filter(Boolean);
  if (missing.length > 0) throw new Error(`Set ${missing.join(" and ")} for the E2E account.`);
  return { email, password };
}

export function runFileName(file: RunFile): string {
  return fileName({
    entity: REPORT_ENTITY,
    what: file.what,
    ext: file.ext,
    date: runStartedAt(),
    time: true,
    subject: file.subject,
    sequence: file.sequence
  });
}

export function writeRunFile(path: string, content: string): string {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content, "utf8");
  return path;
}

export function writeReport(name: string, report: unknown): string {
  return writeRunFile(join(REPORT_DIR, name), `${JSON.stringify(report, null, 2)}\n`);
}
