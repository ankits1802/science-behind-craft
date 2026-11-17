import type { CDPSession, Page } from "@playwright/test";

import { clip } from "./checks";

const PAUSE_WAIT_MS = 5_000;
const FRAMES_SHOWN = 6;
const SOURCE_SPAN = 120;

type CallFrame = {
  functionName: string;
  url: string;
  location: { scriptId: string; lineNumber: number; columnNumber?: number };
};

type Paused = { callFrames: CallFrame[] };

function delay(ms: number): Promise<null> {
  return new Promise((resolve) => setTimeout(() => resolve(null), ms));
}

export async function answersScript(page: Page, withinMs: number): Promise<boolean> {
  const answered = page.evaluate(() => true).catch(() => false);
  return Promise.race([answered, delay(withinMs).then(() => false)]);
}

export async function watchScript(page: Page): Promise<CDPSession> {
  const debuggerSession = await page.context().newCDPSession(page);
  await debuggerSession.send("Debugger.enable");
  return debuggerSession;
}

export async function stuckStack(debuggerSession: CDPSession): Promise<string[]> {
  const paused = new Promise<Paused>((resolve) => debuggerSession.once("Debugger.paused", (event) => resolve(event as Paused)));
  void debuggerSession.send("Debugger.pause").catch(() => undefined);
  const event = await Promise.race([paused, delay(PAUSE_WAIT_MS)]);
  if (event === null) return ["the debugger could not pause it, so the main thread is stuck outside script (style, layout or paint)"];
  const frames = await Promise.all(event.callFrames.slice(0, FRAMES_SHOWN).map((frame) => describeFrame(debuggerSession, frame)));
  await debuggerSession.send("Debugger.resume").catch(() => undefined);
  return frames;
}

async function describeFrame(debuggerSession: CDPSession, frame: CallFrame): Promise<string> {
  const { scriptId, lineNumber, columnNumber = 0 } = frame.location;
  const where = `${frame.functionName || "(anonymous)"} at ${new URL(frame.url || "about:blank").pathname}:${lineNumber + 1}:${columnNumber + 1}`;
  const source = await debuggerSession
    .send("Debugger.getScriptSource", { scriptId })
    .then((found) => (found as { scriptSource: string }).scriptSource)
    .catch(() => "");
  const line = source.split("\n")[lineNumber] ?? "";
  const start = Math.max(0, columnNumber - SOURCE_SPAN / 2);
  return clip(`stuck in ${where}: ${line.slice(start, start + SOURCE_SPAN)}`, 400);
}
