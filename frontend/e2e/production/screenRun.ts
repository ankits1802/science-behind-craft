import { join } from "node:path";

import { expect, type CDPSession, type ConsoleMessage, type Page, type Request, type Response } from "@playwright/test";

import { CITED_CONTENT, OVERFLOW_LIMIT, clip, gapCopyFindings } from "./checks";
import { auditPage } from "./pageAudit";
import type { ScreenOutcome, ScreensReport } from "./report";
import { SCREENSHOT_DIR, baseUrl, runFileName, runId, runStartedAt, writeReport } from "./run";
import { answersScript, stuckStack, watchScript } from "./stuckPage";

export type ScreenCheck = () => Promise<string[]>;

export type VisitOptions = { expectStatus?: number };

const SETTLE_MS = 700;
const IDLE_TIMEOUT_MS = 20_000;
const LOADING_TIMEOUT_MS = 30_000;
const LOADING_TEXT = /^(Loading…|Checking your admin view…)$/;
const STEP_LIMIT_MS = 120_000;
const ANSWER_WAIT_MS = 5_000;

export async function settle(page: Page): Promise<string[]> {
  await page.waitForLoadState("networkidle", { timeout: IDLE_TIMEOUT_MS }).catch(() => undefined);
  const stillLoading = await expect(page.getByText(LOADING_TEXT))
    .toHaveCount(0, { timeout: LOADING_TIMEOUT_MS })
    .then(() => false)
    .catch(() => true);
  await page.waitForTimeout(SETTLE_MS);
  return stillLoading ? [`still loading after ${LOADING_TIMEOUT_MS / 1000} s`] : [];
}

function firstLine(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  return clip(message.split("\n")[0] ?? message);
}

export class ScreenRun {
  readonly screens: ScreenOutcome[] = [];
  private readonly page: Page;
  private readonly width: string;
  private readonly origin: string;
  private signedIn = false;
  private notFoundPath: string | null = null;
  private current: ScreenOutcome | null = null;
  private role: string | null = null;
  private everyScreenCheck: ScreenCheck | null = null;
  private debuggerSession: CDPSession | null = null;
  private stuckSince: string | null = null;

  constructor(page: Page, width: string) {
    this.page = page;
    this.width = width;
    this.origin = new URL(baseUrl()).origin;
    page.on("console", (message) => this.onConsole(message));
    page.on("pageerror", (error) => this.flag(`uncaught error: ${firstLine(error)}`));
    page.on("requestfailed", (request) => this.onRequestFailed(request));
    page.on("response", (response) => this.onResponse(response));
  }

  async watch(): Promise<void> {
    this.debuggerSession = await watchScript(this.page).catch(() => null);
  }

  markSignedIn(role: string | null): void {
    this.signedIn = true;
    this.role = role;
  }

  checkEveryScreen(check: ScreenCheck | null): void {
    this.everyScreenCheck = check;
  }

  flag(...problems: string[]): void {
    this.current?.problems.push(...problems);
  }

  note(...notes: string[]): void {
    this.current?.notes.push(...notes);
  }

  async visit(name: string, path: string, check?: ScreenCheck, options: VisitOptions = {}): Promise<void> {
    await this.screen(name, async () => {
      this.notFoundPath = options.expectStatus === 404 ? path : null;
      const response = await this.page.goto(path, { waitUntil: "domcontentloaded" });
      const expected = options.expectStatus ?? 200;
      const status = response?.status() ?? 0;
      if (status !== expected) this.flag(`the page answered ${status}, expected ${expected}`);
      this.flag(...(await settle(this.page)));
      if (check) this.flag(...(await check()));
      await this.runEveryScreenCheck();
    });
  }

  async step(name: string, action: ScreenCheck): Promise<void> {
    await this.screen(name, async () => {
      this.flag(...(await action()));
      this.flag(...(await settle(this.page)));
      await this.runEveryScreenCheck();
    });
  }

  problemCount(): number {
    return this.screens.reduce((sum, screen) => sum + screen.problems.length, 0);
  }

  problemText(): string {
    return this.screens.flatMap((screen) => screen.problems.map((problem) => `${this.width} · ${screen.name}: ${problem}`)).join("\n");
  }

  write(): string {
    const report: ScreensReport = {
      kind: "screens",
      width: this.width,
      viewport: this.page.viewportSize(),
      baseUrl: baseUrl(),
      runId: runId(),
      startedAt: runStartedAt(),
      role: this.role,
      problemCount: this.problemCount(),
      screens: this.screens
    };
    return writeReport(runFileName({ subject: `${this.width} Screens`, what: "Report", ext: "json" }), report);
  }

  private async screen(name: string, body: () => Promise<void>): Promise<void> {
    const outcome: ScreenOutcome = { name, path: "", screenshot: null, durationMs: 0, problems: [], notes: [] };
    this.current = outcome;
    this.screens.push(outcome);
    if (this.stuckSince) {
      this.flag(`skipped: the page stopped running script during ${this.stuckSince}`);
      return;
    }
    const started = Date.now();
    if (!(await this.bounded(body))) await this.diagnoseStuck(name);
    outcome.path = new URL(this.page.url()).pathname;
    if (!this.stuckSince) {
      outcome.screenshot = await this.capture(name).catch((error: unknown) => {
        this.flag(`no screenshot: ${firstLine(error)}`);
        return null;
      });
    }
    outcome.durationMs = Date.now() - started;
  }

  private async bounded(body: () => Promise<void>): Promise<boolean> {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const limit = new Promise<boolean>((resolve) => {
      timer = setTimeout(() => resolve(false), STEP_LIMIT_MS);
    });
    const work = (async () => {
      await body();
      await this.audit();
    })().then(
      () => true,
      (error: unknown) => {
        this.flag(`could not finish: ${firstLine(error)}`);
        return true;
      }
    );
    const finished = await Promise.race([work, limit]);
    clearTimeout(timer);
    return finished;
  }

  private async diagnoseStuck(name: string): Promise<void> {
    this.flag(`did not finish in ${STEP_LIMIT_MS / 1000} s`);
    if (await answersScript(this.page, ANSWER_WAIT_MS)) return;
    this.stuckSince = name;
    const stack = this.debuggerSession
      ? await stuckStack(this.debuggerSession).catch((error: unknown) => [`no stack: ${firstLine(error)}`])
      : ["no debugger session"];
    this.flag("the page stopped running script", ...stack);
  }

  private async runEveryScreenCheck(): Promise<void> {
    if (this.everyScreenCheck) this.flag(...(await this.everyScreenCheck()));
  }

  private async audit(): Promise<void> {
    const audit = await this.page.evaluate(auditPage, { citedSelector: CITED_CONTENT, limit: OVERFLOW_LIMIT });
    if (audit.pageOverflowPx > 1) this.flag(`the page scrolls sideways by ${audit.pageOverflowPx}px`);
    this.flag(...audit.textOverflow.map((finding) => `text overflow: ${finding}`));
    this.flag(...audit.alerts.map((alert) => `shows an error: ${clip(alert)}`));
    this.flag(...gapCopyFindings(audit.copy).map((finding) => `gap copy: "${finding}"`));
  }

  private async capture(name: string): Promise<string> {
    const file = runFileName({
      subject: `${this.width} ${name}`,
      what: "Snapshot",
      ext: "png",
      sequence: String(this.screens.length).padStart(2, "0")
    });
    await this.page.screenshot({ path: join(SCREENSHOT_DIR, file), fullPage: true });
    return file;
  }

  private sameOrigin(url: string): URL | null {
    const parsed = new URL(url);
    return parsed.origin === this.origin ? parsed : null;
  }

  private onConsole(message: ConsoleMessage): void {
    if (message.type() !== "error") return;
    const text = message.text();
    const from = message.location().url;
    if (text.startsWith("Failed to load resource") && from && this.sameOrigin(from)) return;
    this.flag(`console error: ${clip(text)}`);
  }

  private onRequestFailed(request: Request): void {
    const url = this.sameOrigin(request.url());
    const failure = request.failure()?.errorText ?? "failed";
    if (!url || failure === "net::ERR_ABORTED") return;
    this.flag(`${request.method()} ${url.pathname} failed: ${failure}`);
  }

  private onResponse(response: Response): void {
    const url = this.sameOrigin(response.url());
    const status = response.status();
    if (!url || status < 400) return;
    if (!this.signedIn && status === 401 && url.pathname.startsWith("/api/")) return;
    if (status === 404 && url.pathname === this.notFoundPath && response.request().isNavigationRequest()) return;
    this.flag(`${response.request().method()} ${url.pathname} answered ${status}`);
  }
}
