import { expect, test } from "@playwright/test";

import { blockingScripts, blockingTime, budgetBreaches, layoutShift, medianMeasure, phoneLimit, phoneMeasure, phoneRecord, shortUrl, type PhoneMeasure, type PhoneNumbers, type RawLoad, type Sent, type Shift } from "./phoneBudget";

const ORIGIN = "http://localhost:3000";
const PAGE = "/crafts/Kutch-Ajrakh";

const sent = (path: string, type: string, kib: number): Sent => ({ url: `${ORIGIN}${path}`, type, bytes: kib * 1024 });
const shift = (at: number, value: number, input = false, nodes: string[] = [`div.at-${at}`]): Shift => ({ at, value, input, nodes });

function rawLoad(extra: Sent[] = []): RawLoad {
  return {
    fcp: 1200,
    paints: [
      { at: 1300, node: "h1.kv-q", url: "" },
      { at: 2900, node: "img", url: `${ORIGIN}/_next/image?url=%2Fhero.jpg&w=960&q=80` }
    ],
    shifts: [shift(3000, 0.01)],
    tasks: [
      { at: 1000, duration: 400 },
      { at: 2000, duration: 120 }
    ],
    scripts: [
      { url: `${ORIGIN}/monographs/kit/monograph.js`, duration: 180 },
      { url: `${ORIGIN}/_next/static/chunks/a.js`, duration: 90 },
      { url: `${ORIGIN}/monographs/kit/monograph.js`, duration: 60 }
    ],
    firstScreen: [`${ORIGIN}/_next/image?url=%2Fhero.jpg&w=960&q=80`],
    sent: [
      sent("/crafts/Kutch-Ajrakh", "Document", 40),
      sent("/_next/static/chunks/a.js", "Script", 200),
      sent("/monographs/kit/monograph.js", "Script", 44),
      sent("/monographs/kit/monograph.css", "Stylesheet", 70),
      sent("/_next/image?url=%2Fhero.jpg&w=960&q=80", "Image", 120),
      sent("/_next/image?url=%2Flater.jpg&w=500&q=80", "Image", 30),
      sent("/_next/static/media/newsreader.woff2", "Font", 25),
      ...extra
    ],
    reading: [shift(9000, 0.02, false, ["figure.mol"])]
  };
}

const RECORDED: PhoneNumbers = { scriptBytes: 244 * 1024, styleBytes: 70 * 1024, firstScreenImageBytes: 120 * 1024, lcpMs: 2900, blockingMs: 420, cls: 0.01, readingShift: 0.02 };

test("a task blocks the main thread for what it runs past 50 ms after the first paint", () => {
  expect(blockingTime([{ at: 100, duration: 120 }, { at: 400, duration: 40 }, { at: 900, duration: 300 }], 150)).toBe(270);
  expect(blockingTime([{ at: 0, duration: 100 }], 200)).toBe(0);
  expect(blockingTime([], 0)).toBe(0);
});

test("layout shift is the worst session window, gaps of a second and spans of five seconds apart, input left out", () => {
  const sessions = [shift(0, 0.05), shift(500, 0.03), shift(1700, 0.2, true), shift(3000, 0.04), shift(3500, 0.06)];
  expect(layoutShift(sessions)).toEqual({ score: 0.1, nodes: ["div.at-3000", "div.at-3500"] });
  const steady = [0, 900, 1800, 2700, 3600, 4500, 5400, 6300].map((at) => shift(at, 0.01));
  expect(layoutShift(steady).score).toBe(0.06);
  expect(layoutShift([])).toEqual({ score: 0, nodes: [] });
});

test("a load is measured by what it sent of each kind, its first screen's pictures and its last largest paint", () => {
  const measured = phoneMeasure(rawLoad());
  expect(measured.scriptBytes).toBe(244 * 1024);
  expect(measured.styleBytes).toBe(70 * 1024);
  expect(measured.firstScreenImageBytes).toBe(120 * 1024);
  expect(measured.imageBytes).toBe(150 * 1024);
  expect(measured.documentBytes).toBe(40 * 1024);
  expect(measured.fontBytes).toBe(25 * 1024);
  expect(measured.lcpMs).toBe(2900);
  expect(measured.blockingMs).toBe(220);
  expect(measured.cls).toBe(0.01);
  expect(measured.readingShift).toBe(0.02);
  expect(measured.named.largest).toBe("img (/_next/image?url=%2Fhero.jpg&w=960&q=80)");
  expect(measured.named.blocking).toEqual([
    { url: `${ORIGIN}/monographs/kit/monograph.js`, duration: 240 },
    { url: `${ORIGIN}/_next/static/chunks/a.js`, duration: 90 }
  ]);
  expect(measured.named.movedWhileReading).toEqual(["figure.mol"]);
  expect(() => phoneMeasure({ ...rawLoad(), paints: [] })).toThrow("painted no largest element");
});

test("the limits keep the mobile targets and allow the house slack over a recorded number", () => {
  expect(phoneLimit("lcpMs", 1500)).toBe(2500);
  expect(phoneLimit("lcpMs", 1800)).toBe(2700);
  expect(phoneLimit("lcpMs", 5000)).toBe(7500);
  expect(phoneLimit("blockingMs", 50)).toBe(200);
  expect(phoneLimit("blockingMs", 300)).toBe(600);
  expect(phoneLimit("cls", 0.02)).toBe(0.1);
  expect(phoneLimit("cls", 0.08)).toBe(0.13);
  expect(phoneLimit("readingShift", 0)).toBe(0.1);
  expect(phoneLimit("scriptBytes", 300_000)).toBe(330_000);
  expect(phoneLimit("firstScreenImageBytes", 120 * 1024)).toBe(135_168);
});

test("a page within its recorded numbers passes, and one with an unbudgeted heavy import fails naming the script", () => {
  expect(budgetBreaches(PAGE, phoneMeasure(rawLoad()), RECORDED)).toEqual([]);
  const heavy = phoneMeasure(rawLoad([sent("/_next/static/chunks/3dmol.js", "Script", 640)]));
  expect(budgetBreaches(PAGE, heavy, RECORDED)).toEqual([
    "/crafts/Kutch-Ajrakh sends JavaScript of 884.0 KB, over its budget of 268.4 KB (recorded 244.0 KB); the largest scripts are /_next/static/chunks/3dmol.js 640.0 KB, /_next/static/chunks/a.js 200.0 KB, /monographs/kit/monograph.js 44.0 KB"
  ]);
  expect(budgetBreaches(PAGE, phoneMeasure(rawLoad()), undefined)).toEqual(["/crafts/Kutch-Ajrakh has no recorded phone numbers in e2e/phone-budget.json, so it has no budget"]);
});

test("a slower first screen and a moving layout are named by their element", () => {
  const slow: PhoneMeasure = { ...phoneMeasure(rawLoad()), lcpMs: 4400, cls: 0.2 };
  expect(budgetBreaches(PAGE, slow, RECORDED)).toEqual([
    "/crafts/Kutch-Ajrakh paints its largest element at 4400 ms, over its budget of 4350 ms (recorded 2900 ms); the largest element is img (/_next/image?url=%2Fhero.jpg&w=960&q=80)",
    "/crafts/Kutch-Ajrakh moves its layout as it loads by 0.2, over its budget of 0.1 (recorded 0.01); what moved: div.at-3000"
  ]);
});

test("three runs give their median, and the reading run's movement", () => {
  const base = phoneMeasure(rawLoad());
  const runs = [
    { ...base, lcpMs: 3100, blockingMs: 600, readingShift: 0, named: { ...base.named, movedWhileReading: [] } },
    { ...base, lcpMs: 2700, blockingMs: 300, readingShift: 0, named: { ...base.named, movedWhileReading: [] } },
    { ...base, lcpMs: 2900, blockingMs: 900 }
  ];
  const median = medianMeasure(runs);
  expect(median.lcpMs).toBe(2900);
  expect(median.blockingMs).toBe(600);
  expect(median.readingShift).toBe(0.02);
  expect(median.named.movedWhileReading).toEqual(["figure.mol"]);
  expect(() => medianMeasure([])).toThrow("at least one run");
});

test("scripts are named by their address on the site, a picture with its widths", () => {
  expect(shortUrl(`${ORIGIN}/_next/static/chunks/a.js?v=1`)).toBe("/_next/static/chunks/a.js");
  expect(shortUrl(`${ORIGIN}/_next/image?url=%2Fhero.jpg&w=960&q=80`)).toBe("/_next/image?url=%2Fhero.jpg&w=960&q=80");
  expect(shortUrl("inline")).toBe("inline");
  expect(blockingScripts([{ url: "inline", duration: 10.4 }, { url: "inline", duration: 20.3 }])).toEqual([{ url: "inline", duration: 31 }]);
});

test("the recorded budget reads as its shape", () => {
  const record = phoneRecord();
  expect(record.schemaVersion).toBe(1);
  expect(() => phoneRecord('{"schemaVersion": 1, "recordedAt": "x", "run": 1, "pages": {"/a": {"scriptBytes": -1}}}')).toThrow();
});
