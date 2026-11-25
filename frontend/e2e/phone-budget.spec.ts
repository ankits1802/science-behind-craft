import { mkdirSync, writeFileSync } from "node:fs";

import { expect, test, type Browser } from "@playwright/test";

import { budgetBreaches, measuredNumbers, measureLine, medianMeasure, PHONE_PAGES, phoneMeasure, phoneRecord, recordedNumbers, type PhoneMeasure } from "./phoneBudget";
import { phoneLoad, unloadedHeavyChunk, warmed, withScript, type PhoneVisit } from "./phoneMeasure";
import { paintPath, pathLine, type PaintPath } from "./phonePath";
import { smokeApiAddress } from "./smokeApi";

const RUNS = 3;
const PAGE_TIMEOUT_MS = 10 * 60_000;

test.beforeAll(() => {
  test.skip(smokeApiAddress() === null, "measures the local build with its API at a local address");
});

function keep(name: string, value: unknown): void {
  mkdirSync(test.info().outputDir, { recursive: true });
  writeFileSync(test.info().outputPath(name), JSON.stringify(value, null, 1));
}

async function measured(browser: Browser, path: string): Promise<{ measure: PhoneMeasure; paths: PaintPath[] }> {
  const runs: PhoneMeasure[] = [];
  const paths: PaintPath[] = [];
  for (let run = 1; run <= RUNS; run += 1) {
    const visit: PhoneVisit = { read: run === RUNS };
    const raw = await phoneLoad(browser, path, visit);
    runs.push(phoneMeasure(raw));
    paths.push(paintPath(raw));
  }
  return { measure: medianMeasure(runs), paths };
}

for (const path of PHONE_PAGES) {
  test(`${path} on a slowed phone at 360 stays within its recorded budget`, async ({ browser }) => {
    test.setTimeout(PAGE_TIMEOUT_MS);
    await warmed(browser, path);
    const { measure, paths } = await measured(browser, path);
    keep("phone-measure.json", { path, numbers: measuredNumbers(measure), measure, paths });
    console.log(measureLine(path, measure));
    for (const found of paths) console.log(`${path} ${pathLine(found)}`);
    const breaches = budgetBreaches(path, measure, recordedNumbers(phoneRecord(), path));
    expect(breaches, breaches.join("\n")).toEqual([]);
  });
}

test("a heavy import no budget allows for breaks Kutch Ajrakh's phone budget, named", async ({ browser }) => {
  test.setTimeout(PAGE_TIMEOUT_MS);
  const [path] = PHONE_PAGES;
  await warmed(browser, path);
  const plain = await phoneLoad(browser, path, { read: false });
  const heavy = unloadedHeavyChunk(plain.sent);
  const loaded = phoneMeasure(await phoneLoad(browser, path, { read: false, prepare: withScript(path, heavy) }));
  const breaches = budgetBreaches(path, loaded, recordedNumbers(phoneRecord(), path));
  keep("phone-heavy-import.json", { path, heavy, numbers: measuredNumbers(loaded), breaches });
  const scripts = breaches.filter((line) => line.includes("sends JavaScript of"));
  expect(scripts, breaches.join("\n")).toHaveLength(1);
  expect(scripts[0]).toContain(heavy);
});
