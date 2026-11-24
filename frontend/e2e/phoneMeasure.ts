import { readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

import type { Browser, CDPSession, Page } from "@playwright/test";

import { FRONTEND } from "./moduleGraph";
import type { RawLoad, Sent, Shift, Watched } from "./phoneBudget";
import { contextOptions, SMALL_PHONE } from "./production/matrix";

export const PHONE_THROTTLING = { cpuSlowdown: 4, requestLatencyMs: 562.5, downloadKbps: 1474.56, uploadKbps: 675 } as const;

const BYTES_PER_KBIT = 1024 / 8;
const SETTLE_TIMEOUT_MS = 90_000;
const QUIET_MS = 2_000;
const POLL_MS = 250;
const READ_STEP = 0.8;
const READ_PAUSE_MS = 300;
const READ_STEPS = 150;
const CHUNKS = join(FRONTEND, ".next", "static", "chunks");
const CHUNK_PATH = "/_next/static/chunks/";

type Watch = Omit<Watched, "fcp" | "firstScreen">;
export type PhoneVisit = { read: boolean; prepare?: (page: Page) => Promise<void> };

declare global {
  interface Window {
    __kvPhone?: Watch;
  }
}

function watchPerformance(): void {
  const watch: Watch = { paints: [], shifts: [], tasks: [], scripts: [] };
  window.__kvPhone = watch;
  const named = (node: unknown): string => {
    if (!(node instanceof Element)) return "text";
    const classes = Array.from(node.classList).slice(0, 2).map((name) => `.${name}`).join("");
    return `${node.tagName.toLowerCase()}${node.id ? `#${node.id}` : ""}${classes}`;
  };
  const observe = (type: string, take: (entry: PerformanceEntry) => void) => new PerformanceObserver((list) => list.getEntries().forEach(take)).observe({ type, buffered: true });
  observe("largest-contentful-paint", (entry) => {
    const paint = entry as PerformanceEntry & { element?: Element | null; url?: string };
    watch.paints.push({ at: paint.startTime, node: named(paint.element), url: paint.url ?? "" });
  });
  observe("layout-shift", (entry) => {
    const shift = entry as PerformanceEntry & { value: number; hadRecentInput: boolean; sources?: { node?: Node | null }[] };
    watch.shifts.push({ at: shift.startTime, value: shift.value, input: shift.hadRecentInput, nodes: (shift.sources ?? []).map((source) => named(source.node)) });
  });
  observe("longtask", (entry) => watch.tasks.push({ at: entry.startTime, duration: entry.duration }));
  observe("long-animation-frame", (entry) => {
    const frame = entry as PerformanceEntry & { scripts?: { sourceURL?: string; invoker?: string; duration: number }[] };
    for (const script of frame.scripts ?? []) watch.scripts.push({ url: script.sourceURL || script.invoker || "inline", duration: script.duration });
  });
}

async function throttled(page: Page): Promise<CDPSession> {
  const session = await page.context().newCDPSession(page);
  await session.send("Network.enable");
  await session.send("Network.emulateNetworkConditions", {
    offline: false,
    latency: PHONE_THROTTLING.requestLatencyMs,
    downloadThroughput: PHONE_THROTTLING.downloadKbps * BYTES_PER_KBIT,
    uploadThroughput: PHONE_THROTTLING.uploadKbps * BYTES_PER_KBIT
  });
  await session.send("Emulation.setCPUThrottlingRate", { rate: PHONE_THROTTLING.cpuSlowdown });
  return session;
}

function transfers(session: CDPSession): () => Sent[] {
  const answered = new Map<string, { url: string; type: string }>();
  const sent: Sent[] = [];
  session.on("Network.responseReceived", (event) => answered.set(event.requestId, { url: event.response.url, type: event.type }));
  session.on("Network.loadingFinished", (event) => {
    const found = answered.get(event.requestId);
    if (found) sent.push({ ...found, bytes: event.encodedDataLength });
  });
  return () => [...sent];
}

async function complete(page: Page): Promise<void> {
  await page.waitForFunction(() => "KV" in window && document.querySelector("[data-kv-deferred]") === null, undefined, { timeout: SETTLE_TIMEOUT_MS, polling: POLL_MS });
}

async function quiet(page: Page): Promise<void> {
  await page.waitForFunction(
    (wait) => (window.__kvPhone?.tasks ?? []).every((task) => performance.now() - (task.at + task.duration) >= wait),
    QUIET_MS,
    { timeout: SETTLE_TIMEOUT_MS, polling: POLL_MS }
  );
}

async function watched(page: Page): Promise<Watched> {
  return page.evaluate(() => {
    const watch = window.__kvPhone ?? { paints: [], shifts: [], tasks: [], scripts: [] };
    const fcp = performance.getEntriesByName("first-contentful-paint")[0]?.startTime ?? 0;
    const shown = Array.from(document.images).filter((image) => {
      const box = image.getBoundingClientRect();
      return image.currentSrc !== "" && box.width > 0 && box.height > 0 && box.bottom > 0 && box.top < window.innerHeight;
    });
    return { ...watch, paints: [...watch.paints], shifts: [...watch.shifts], tasks: [...watch.tasks], scripts: [...watch.scripts], fcp, firstScreen: shown.map((image) => image.currentSrc) };
  });
}

async function readThrough(page: Page): Promise<Shift[]> {
  const before = await page.evaluate(() => window.__kvPhone?.shifts.length ?? 0);
  await page.evaluate(
    async ({ step, pause, steps }) => {
      for (let at = 0; at < steps && window.scrollY + window.innerHeight < document.documentElement.scrollHeight; at += 1) {
        window.scrollBy(0, Math.round(window.innerHeight * step));
        await new Promise((resolve) => setTimeout(resolve, pause));
      }
    },
    { step: READ_STEP, pause: READ_PAUSE_MS, steps: READ_STEPS }
  );
  await quiet(page);
  return page.evaluate((from) => (window.__kvPhone?.shifts ?? []).slice(from), before);
}

export async function phoneLoad(browser: Browser, path: string, visit: PhoneVisit): Promise<RawLoad> {
  const context = await browser.newContext(contextOptions(SMALL_PHONE, "light"));
  try {
    await context.addInitScript(watchPerformance);
    const page = await context.newPage();
    if (visit.prepare) await visit.prepare(page);
    const sent = transfers(await throttled(page));
    await page.goto(path, { waitUntil: "load", timeout: SETTLE_TIMEOUT_MS });
    await complete(page);
    await quiet(page);
    const loaded = await watched(page);
    const reading = visit.read ? await readThrough(page) : null;
    return { ...loaded, sent: sent(), reading };
  } finally {
    await context.close();
  }
}

export async function warmed(browser: Browser, path: string): Promise<void> {
  const context = await browser.newContext(contextOptions(SMALL_PHONE, "light"));
  try {
    const page = await context.newPage();
    await page.goto(path, { waitUntil: "load", timeout: SETTLE_TIMEOUT_MS });
    await complete(page);
  } finally {
    await context.close();
  }
}

function chunkFiles(folder: string): string[] {
  return readdirSync(folder, { withFileTypes: true }).flatMap((entry) => {
    const found = join(folder, entry.name);
    if (entry.isDirectory()) return chunkFiles(found);
    return entry.name.endsWith(".js") ? [found] : [];
  });
}

export function unloadedHeavyChunk(loaded: readonly Sent[]): string {
  const taken = new Set(loaded.filter((item) => item.type === "Script").map((item) => new URL(item.url).pathname));
  const chunks = chunkFiles(CHUNKS)
    .map((file) => ({ path: `${CHUNK_PATH}${relative(CHUNKS, file).replace(/\\/g, "/")}`, bytes: statSync(file).size }))
    .filter((chunk) => !taken.has(chunk.path))
    .sort((left, right) => right.bytes - left.bytes);
  if (!chunks[0]) throw new Error(`The build in ${CHUNKS} holds no chunk the page did not load`);
  return chunks[0].path;
}

export function withScript(path: string, script: string): (page: Page) => Promise<void> {
  return (page) =>
    page.route(
      (url) => url.pathname === path,
      async (route) => {
        const response = await route.fetch();
        const body = (await response.text()).replace("</body>", `<script src="${script}" async></script></body>`);
        await route.fulfill({ response, body });
      }
    );
}
