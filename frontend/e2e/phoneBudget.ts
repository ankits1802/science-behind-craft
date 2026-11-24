import { readFileSync } from "node:fs";
import { join } from "node:path";

import { count, dictionary, number, object, oneOf, parseShape, text } from "../lib/shape";

import { CLS_SLACK, LIGHTHOUSE_TARGETS, METRIC_SLACK } from "./release/auditBudgets";

export const PHONE_PAGES = ["/crafts/Kutch-Ajrakh", "/crafts/Phone-Fixtures"] as const;
export const BUDGETED = ["scriptBytes", "styleBytes", "firstScreenImageBytes", "lcpMs", "blockingMs", "cls", "readingShift"] as const;
export const PHONE_RECORD = join(__dirname, "phone-budget.json");

export type Budgeted = (typeof BUDGETED)[number];
export type PhoneNumbers = Record<Budgeted, number>;
export type PhoneRecord = { schemaVersion: 1; recordedAt: string; run: number; pages: Record<string, PhoneNumbers> };

export type Sent = { url: string; type: string; bytes: number };
export type Shift = { at: number; value: number; input: boolean; nodes: string[] };
export type Task = { at: number; duration: number };
export type FrameScript = { url: string; duration: number };
export type Paint = { at: number; node: string; url: string };
export type Watched = { fcp: number; paints: Paint[]; shifts: Shift[]; tasks: Task[]; scripts: FrameScript[]; firstScreen: string[] };
export type RawLoad = Watched & { sent: Sent[]; reading: Shift[] | null };

export type Named = { scripts: Sent[]; styles: Sent[]; firstScreenImages: Sent[]; largest: string; shifted: string[]; blocking: FrameScript[]; movedWhileReading: string[] };
export type PhoneMeasure = PhoneNumbers & { imageBytes: number; documentBytes: number; fontBytes: number; named: Named };

const LONG_TASK_MS = 50;
const SESSION_GAP_MS = 1000;
const SESSION_SPAN_MS = 5000;
const NAMED_COUNT = 5;
const SHIFT_DIGITS = 4;
const KIB = 1024;
const TARGETS = LIGHTHOUSE_TARGETS.mobile.metrics;
const ON_THE_IMAGE_SERVICE = "/_next/image";
const ADDRESS = /^https?:\/\/[^/\s]+/;

const numbersShape = object<PhoneNumbers>({ scriptBytes: count, styleBytes: count, firstScreenImageBytes: count, lcpMs: count, blockingMs: count, cls: number, readingShift: number });
const recordShape = object<PhoneRecord>({ schemaVersion: oneOf([1] as const), recordedAt: text, run: count, pages: dictionary(/^\/[\w/-]+$/, numbersShape) });

export function phoneRecord(source: string = readFileSync(PHONE_RECORD, "utf8")): PhoneRecord {
  return parseShape(recordShape, JSON.parse(source));
}

function rounded(value: number, digits: number): number {
  const scale = 10 ** digits;
  return Math.round(value * scale) / scale;
}

export function blockingTime(tasks: readonly Task[], from: number): number {
  return tasks.reduce((total, task) => total + Math.max(0, task.at + task.duration - Math.max(task.at, from) - LONG_TASK_MS), 0);
}

type Session = { start: number; last: number; score: number; nodes: string[] };

const NO_SESSION: Session = { start: Number.NEGATIVE_INFINITY, last: Number.NEGATIVE_INFINITY, score: 0, nodes: [] };

function joined(session: Session, shift: Shift): Session {
  const fresh = shift.at - session.last >= SESSION_GAP_MS || shift.at - session.start >= SESSION_SPAN_MS;
  if (fresh) return { start: shift.at, last: shift.at, score: shift.value, nodes: [...shift.nodes] };
  return { start: session.start, last: shift.at, score: session.score + shift.value, nodes: [...session.nodes, ...shift.nodes] };
}

export function layoutShift(shifts: readonly Shift[]): { score: number; nodes: string[] } {
  let best = NO_SESSION;
  let session = NO_SESSION;
  for (const shift of shifts.filter((found) => !found.input).sort((left, right) => left.at - right.at)) {
    session = joined(session, shift);
    if (session.score > best.score) best = session;
  }
  return { score: rounded(best.score, SHIFT_DIGITS), nodes: [...new Set(best.nodes)] };
}

function total(sent: readonly Sent[]): number {
  return sent.reduce((sum, item) => sum + item.bytes, 0);
}

function heaviest(sent: readonly Sent[]): Sent[] {
  return [...sent].sort((left, right) => right.bytes - left.bytes).slice(0, NAMED_COUNT);
}

function onePerAddress(sent: readonly Sent[]): Sent[] {
  return [...new Map(sent.map((item) => [item.url, item])).values()];
}

export function blockingScripts(scripts: readonly FrameScript[]): FrameScript[] {
  const byUrl = new Map<string, number>();
  for (const script of scripts) byUrl.set(script.url, (byUrl.get(script.url) ?? 0) + script.duration);
  return [...byUrl].map(([url, duration]) => ({ url, duration: Math.round(duration) })).sort((left, right) => right.duration - left.duration).slice(0, NAMED_COUNT);
}

export function phoneMeasure(raw: RawLoad): PhoneMeasure {
  const largest = raw.paints[raw.paints.length - 1];
  if (!largest) throw new Error("The page painted no largest element, so its first screen cannot be timed");
  const of = (type: string) => raw.sent.filter((item) => item.type === type);
  const shown = new Set(raw.firstScreen);
  const firstScreenImages = onePerAddress(of("Image").filter((item) => shown.has(item.url)));
  const loadShift = layoutShift(raw.shifts);
  const reading = layoutShift(raw.reading ?? []);
  return {
    scriptBytes: total(of("Script")),
    styleBytes: total(of("Stylesheet")),
    firstScreenImageBytes: total(firstScreenImages),
    lcpMs: Math.round(largest.at),
    blockingMs: Math.round(blockingTime(raw.tasks, raw.fcp)),
    cls: loadShift.score,
    readingShift: reading.score,
    imageBytes: total(of("Image")),
    documentBytes: total(of("Document")),
    fontBytes: total(of("Font")),
    named: { scripts: heaviest(of("Script")), styles: heaviest(of("Stylesheet")), firstScreenImages: heaviest(firstScreenImages), largest: largest.url ? `${largest.node} (${shortUrl(largest.url)})` : largest.node, shifted: loadShift.nodes, blocking: blockingScripts(raw.scripts), movedWhileReading: reading.nodes }
  };
}

function middle<T>(items: readonly T[], value: (item: T) => number): T {
  return [...items].sort((left, right) => value(left) - value(right))[Math.floor((items.length - 1) / 2)];
}

export function medianMeasure(runs: readonly PhoneMeasure[]): PhoneMeasure {
  if (runs.length === 0) throw new Error("A phone measure needs at least one run");
  const typical = middle(runs, (run) => run.blockingMs);
  const read = runs.find((run) => run.named.movedWhileReading.length > 0 || run.readingShift > 0) ?? typical;
  const median = (key: Exclude<keyof PhoneMeasure, "named">) => middle(runs, (run) => run[key])[key];
  return {
    scriptBytes: median("scriptBytes"),
    styleBytes: median("styleBytes"),
    firstScreenImageBytes: median("firstScreenImageBytes"),
    lcpMs: median("lcpMs"),
    blockingMs: median("blockingMs"),
    cls: median("cls"),
    readingShift: Math.max(...runs.map((run) => run.readingShift)),
    imageBytes: median("imageBytes"),
    documentBytes: median("documentBytes"),
    fontBytes: median("fontBytes"),
    named: { ...typical.named, movedWhileReading: read.named.movedWhileReading }
  };
}

export function phoneLimit(metric: Budgeted, recorded: number): number {
  if (metric === "lcpMs") return Math.max(TARGETS.lcpMs, Math.round(recorded * METRIC_SLACK.lcpMs));
  if (metric === "blockingMs") return Math.max(TARGETS.tbtMs, Math.round(recorded * METRIC_SLACK.tbtMs));
  if (metric === "cls" || metric === "readingShift") return Math.max(TARGETS.cls, rounded(recorded + CLS_SLACK, 3));
  return Math.round(recorded * METRIC_SLACK.bytes);
}

export function shortUrl(url: string): string {
  if (!ADDRESS.test(url)) return url;
  const parsed = new URL(url);
  return parsed.pathname === ON_THE_IMAGE_SERVICE ? `${parsed.pathname}${parsed.search}` : parsed.pathname;
}

export function kilobytes(bytes: number): string {
  return `${(bytes / KIB).toFixed(1)} KB`;
}

const sentList = (sent: readonly Sent[]) => sent.map((item) => `${shortUrl(item.url)} ${kilobytes(item.bytes)}`).join(", ") || "none";

const NAMES: Record<Budgeted, { what: string; shown: (value: number) => string; grew: (named: Named) => string }> = {
  scriptBytes: { what: "sends JavaScript of", shown: kilobytes, grew: (named) => `the largest scripts are ${sentList(named.scripts)}` },
  styleBytes: { what: "sends CSS of", shown: kilobytes, grew: (named) => `the largest stylesheets are ${sentList(named.styles)}` },
  firstScreenImageBytes: { what: "draws first-screen pictures of", shown: kilobytes, grew: (named) => `the first screen shows ${sentList(named.firstScreenImages)}` },
  lcpMs: { what: "paints its largest element at", shown: (value) => `${value} ms`, grew: (named) => `the largest element is ${named.largest}` },
  blockingMs: { what: "blocks the main thread for", shown: (value) => `${value} ms`, grew: (named) => `the scripts that ran longest are ${named.blocking.map((script) => `${shortUrl(script.url)} ${script.duration} ms`).join(", ") || "not named by the browser"}` },
  cls: { what: "moves its layout as it loads by", shown: String, grew: (named) => `what moved: ${named.shifted.join(", ") || "not named by the browser"}` },
  readingShift: { what: "moves its layout while it is read by", shown: String, grew: (named) => `what moved: ${named.movedWhileReading.join(", ") || "not named by the browser"}` }
};

export function budgetBreaches(path: string, measured: PhoneMeasure, recorded: PhoneNumbers | undefined): string[] {
  if (!recorded) return [`${path} has no recorded phone numbers in e2e/phone-budget.json, so it has no budget`];
  return BUDGETED.flatMap((metric) => {
    const limit = phoneLimit(metric, recorded[metric]);
    const value = measured[metric];
    if (value <= limit) return [];
    const name = NAMES[metric];
    return [`${path} ${name.what} ${name.shown(value)}, over its budget of ${name.shown(limit)} (recorded ${name.shown(recorded[metric])}); ${name.grew(measured.named)}`];
  });
}

export function recordedNumbers(record: PhoneRecord, path: string): PhoneNumbers | undefined {
  return Object.hasOwn(record.pages, path) ? record.pages[path] : undefined;
}

export function measuredNumbers(measured: PhoneMeasure): PhoneNumbers {
  return Object.fromEntries(BUDGETED.map((metric) => [metric, measured[metric]])) as PhoneNumbers;
}

export function measureLine(path: string, measured: PhoneMeasure): string {
  const parts = [
    `JavaScript ${kilobytes(measured.scriptBytes)}`,
    `CSS ${kilobytes(measured.styleBytes)}`,
    `first-screen pictures ${kilobytes(measured.firstScreenImageBytes)} of ${kilobytes(measured.imageBytes)}`,
    `largest element ${measured.lcpMs} ms`,
    `main thread blocked ${measured.blockingMs} ms`,
    `layout shift ${measured.cls} loading and ${measured.readingShift} reading`,
    `document ${kilobytes(measured.documentBytes)}`,
    `fonts ${kilobytes(measured.fontBytes)}`
  ];
  return `${path} on a slowed phone at 360: ${parts.join("; ")}`;
}
