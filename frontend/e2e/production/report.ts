import type { AnswerRecord } from "./answers";
import type { ExportProof } from "./exportProof";

export type ScreenOutcome = {
  name: string;
  path: string;
  screenshot: string | null;
  durationMs: number;
  problems: string[];
  notes: string[];
};

export type ScreensReport = {
  kind: "screens";
  width: string;
  viewport: { width: number; height: number } | null;
  baseUrl: string;
  runId: string | null;
  startedAt: string;
  role: string | null;
  problemCount: number;
  screens: ScreenOutcome[];
};

export type AnswersReport = {
  kind: "answers";
  baseUrl: string;
  runId: string | null;
  startedAt: string;
  role: string | null;
  problemCount: number;
  unasked: string[];
  questions: AnswerRecord[];
  exports: ExportProof | null;
};

export type RunReport = ScreensReport | AnswersReport;
