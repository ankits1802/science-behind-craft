import type { AnswerRecord } from "./answers";
import type { AnswersReport, RunReport, ScreensReport } from "./report";

export type SummaryContext = { runId: string | null; baseUrl: string | null; startedAt: string; questionsRequested: boolean };

const PROBLEM_LINES = 40;

function cell(value: string): string {
  return value.replace(/\|/g, "\\|").replace(/\s+/g, " ").trim();
}

function verdict(problems: number): string {
  return problems === 0 ? "Pass" : `Fail (${problems})`;
}

function seconds(ms: number | null): string {
  return ms === null ? "-" : `${Math.round(ms / 1000)} s`;
}

function screensSection(reports: ScreensReport[]): string[] {
  if (reports.length === 0) return ["### Screens", "", "No screens report was written."];
  const names = [...new Set(reports.flatMap((report) => report.screens.map((screen) => screen.name)))];
  const lines = ["### Screens", "", `| Screen | ${reports.map((report) => cell(report.width)).join(" | ")} |`, `|---|${reports.map(() => "---").join("|")}|`];
  for (const name of names) {
    const row = reports.map((report) => {
      const screen = report.screens.find((entry) => entry.name === name);
      return screen ? verdict(screen.problems.length) : "Not reached";
    });
    lines.push(`| ${cell(name)} | ${row.join(" | ")} |`);
  }
  const problems = reports.flatMap((report) => report.screens.flatMap((screen) => screen.problems.map((problem) => `- ${cell(report.width)} · ${cell(screen.name)}: ${cell(problem)}`)));
  if (problems.length > 0) lines.push("", "#### Screen problems", "", ...problems.slice(0, PROBLEM_LINES));
  if (problems.length > PROBLEM_LINES) lines.push(`- and ${problems.length - PROBLEM_LINES} more in the JSON reports`);
  return lines;
}

function scriptCell(record: AnswerRecord): string {
  if (record.expectedLanguage === "en") return "English";
  return `${record.scripts.translated} translated, ${record.scripts.englishFallback} English, ${record.scripts.other} other`;
}

function questionsSection(report: AnswersReport | undefined, requested: boolean): string[] {
  if (!requested) return ["### Questions", "", "Not asked: dispatch with questions=true to ask them."];
  if (!report) return ["### Questions", "", "No answers report was written."];
  const lines = [
    "### Questions",
    "",
    "| Question | Ended | Sentences | Cited | Citations | Sources | Known answer | Script | Done in | Result |",
    "|---|---|---|---|---|---|---|---|---|---|"
  ];
  for (const record of report.questions) {
    lines.push(
      `| ${cell(record.label)} | ${record.endedWith} | ${record.sentenceCount} | ${record.citedSentenceCount} | ${record.citationCount} | ${record.sources.length} | ${record.knownAnswerFound ? "Yes" : "No"} | ${scriptCell(record)} | ${seconds(record.timing.doneMs)} | ${verdict(record.problems.length)} |`
    );
  }
  const problems = [...report.unasked, ...report.questions.flatMap((record) => record.problems.map((problem) => `${record.label}: ${problem}`))];
  if (problems.length > 0) lines.push("", "#### Answer problems", "", ...problems.map((problem) => `- ${cell(problem)}`));
  const notes = report.questions.flatMap((record) => record.notes.map((note) => `${record.label}: ${note}`));
  if (notes.length > 0) lines.push("", "#### Answer notes", "", ...notes.map((note) => `- ${cell(note)}`));
  return lines;
}

export function summaryMarkdown(reports: readonly RunReport[], context: SummaryContext): string {
  const screens = reports
    .filter((report): report is ScreensReport => report.kind === "screens")
    .sort((a, b) => (b.viewport?.width ?? 0) - (a.viewport?.width ?? 0));
  const answers = reports.find((report): report is AnswersReport => report.kind === "answers");
  const where = context.baseUrl ? ` against ${context.baseUrl}` : "";
  const run = context.runId ? `Run ${context.runId}` : "Local run";
  return [
    "## E2E production",
    "",
    `${run}${where}, started ${context.startedAt}.`,
    "",
    ...screensSection(screens),
    "",
    ...questionsSection(answers, context.questionsRequested),
    ""
  ].join("\n");
}
