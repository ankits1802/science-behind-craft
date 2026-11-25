import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { afterLoad, laterWhenIdle, whenIdle } from "../components/monograph/useShellTrigger";
import type { DocumentLanguageCode } from "../lib/documentLanguages";
import type { MonographDocument } from "../lib/monographDocument";
import { documentPart, documentPartPath, DocumentPartError, joinedDocument, LATEST_READ, laterRead, type DocumentPart } from "../lib/monographDocumentParts";
import { documentDigest, documentRest, restAddress, shellRest, type RestAddress } from "../lib/monographRenderShell";
import { addressedDocument, fetchedDocumentRest, fetchedShellRest, REST_UNREAD, type DocumentReader, type RestFetcher } from "../lib/monographRestRead";

import { generatedDocument } from "./generatedMonographFixture";
import { goldenDocument } from "./monographNative";

const part = (at: number, parts: number, body: Record<string, unknown>, version = 4, tag: string | null = null): DocumentPart => ({ schemaVersion: 1, version, part: at, parts, tag, body });
const HINDI_TAG = "v4-abc-hi-0123456789abcdef";
const REST_ROUTE = (pages: string) => join(__dirname, "..", "app", "(reading)", pages, "[slug]", "shell", "[version]", "route.ts");
const CURRENT = "current";

type Reads = { asked: string[]; read: (language: DocumentLanguageCode | null, version: number | null) => Promise<MonographDocument | null> };

function reads(found: Record<string, MonographDocument>): Reads {
  const asked: string[] = [];
  const read = async (language: DocumentLanguageCode | null, version: number | null) => {
    const key = `${language ?? "en"} ${version ?? CURRENT}`;
    asked.push(key);
    return found[key] ?? null;
  };
  return { asked, read };
}

function at(version: number, language = "en"): MonographDocument {
  return { ...generatedDocument(), version, language, subjectKind: "category" };
}

function address(document: MonographDocument, language: DocumentLanguageCode | null = null): RestAddress {
  const found = restAddress(`v${document.version}-${documentDigest(document)}${language ? `-${language}` : ""}`);
  if (found === null) throw new Error("a rest address that does not read back");
  return found;
}

test("a part is read by its number at the version the first part named", () => {
  expect(documentPartPath("/crafts/Kutch-Ajrakh/monograph", 0, LATEST_READ)).toBe("/crafts/Kutch-Ajrakh/monograph?part=0");
  expect(documentPartPath("/crafts/Kutch-Ajrakh/monograph", 2, { ...LATEST_READ, version: 7 })).toBe("/crafts/Kutch-Ajrakh/monograph?version=7&part=2");
});

test("a translated document's later parts are read in its language at the tag its first part named", () => {
  expect(documentPartPath("/crafts/Kutch-Ajrakh/monograph", 0, { ...LATEST_READ, language: "hi" })).toBe("/crafts/Kutch-Ajrakh/monograph?lang=hi&part=0");
  const first = documentPart({ schemaVersion: 1, version: 4, part: 0, parts: 2, tag: HINDI_TAG, body: { language: "hi" } });
  expect(first.tag).toBe(HINDI_TAG);
  expect(documentPartPath("/crafts/Kutch-Ajrakh/monograph", 1, laterRead(first, "hi"))).toBe(`/crafts/Kutch-Ajrakh/monograph?lang=hi&version=4&tag=${HINDI_TAG}&part=1`);
  expect(() => documentPart({ schemaVersion: 1, version: 4, part: 0, parts: 2, tag: 7, body: {} })).toThrow(DocumentPartError);
});

test("a server that sends the whole document is read as its only part", () => {
  const whole = { schemaVersion: 1, subjectSlug: "Kutch-Ajrakh", version: 3, specs: { a: { x: 1 } }, fragments: {}, shell: null };
  expect(documentPart(whole)).toEqual({ schemaVersion: 1, version: 3, part: 0, parts: 1, tag: null, body: whole });
  expect(joinedDocument([documentPart(whole)])).toEqual(whole);
  expect(documentPart({ schemaVersion: 1, version: 3, part: 1, parts: 3, body: { specs: {} } })).toEqual(part(1, 3, { specs: {} }, 3));
  expect(() => documentPart({ schemaVersion: 1, version: 3, part: 3, parts: 3, body: {} })).toThrow(DocumentPartError);
  expect(() => documentPart([1, 2])).toThrow(DocumentPartError);
});

test("the parts join back into the whole document, its shell and specs in their order", () => {
  const joined = joinedDocument([
    part(0, 3, { title: "Kutch Ajrakh", content: { units: {} } }),
    part(1, 3, { shell: "<section></section>", specs: { first: { t: "a" } }, fragments: {} }),
    part(2, 3, { specs: { second: { t: "b" } }, fragments: { frag: "<p></p>" } })
  ]);
  expect(joined).toEqual({ title: "Kutch Ajrakh", content: { units: {} }, shell: "<section></section>", specs: { first: { t: "a" }, second: { t: "b" } }, fragments: { frag: "<p></p>" } });
  expect(Object.keys(joined.specs as object)).toEqual(["first", "second"]);
});

test("parts read from two readings, or too few of them, refuse to join", () => {
  expect(() => joinedDocument([part(0, 2, {}), part(1, 2, { specs: {} }, 5)])).toThrow("from another reading");
  expect(() => joinedDocument([part(0, 2, { language: "hi" }, 4, HINDI_TAG), part(1, 2, { shell: "<section></section>" }, 4, "v4-abc")])).toThrow("from another reading");
  expect(joinedDocument([part(0, 2, { language: "hi" }, 4, HINDI_TAG), part(1, 2, { shell: "<section></section>" }, 4, HINDI_TAG)]).shell).toBe("<section></section>");
  expect(() => joinedDocument([part(0, 3, {}), part(1, 3, { specs: {} })])).toThrow("has 3 parts, not 2");
  expect(() => joinedDocument([part(1, 2, {})])).toThrow("from its first part");
});

test("the rest of a page starts a while after load, once the browser is idle", () => {
  const calls: string[] = [];
  const timers: (() => void)[] = [];
  const setTimeout = (run: () => void, wait: number) => {
    calls.push(`wait ${wait}`);
    timers.push(run);
    return 3;
  };
  const requestIdleCallback = (run: () => void, options: { timeout: number }) => {
    calls.push(`idle ${options.timeout}`);
    run();
    return 1;
  };
  const view = { setTimeout, clearTimeout: () => calls.push("cleared"), requestIdleCallback, cancelIdleCallback: () => calls.push("cancelled") };
  const stop = laterWhenIdle(view as unknown as Window, () => calls.push("started"));
  expect(calls).toEqual(["wait 5000"]);
  timers.forEach((run) => run());
  stop();
  expect(calls).toEqual(["wait 5000", "idle 2000", "started", "cleared", "cancelled"]);
  const plain: string[] = [];
  const runAtOnce = (run: () => void) => {
    run();
    return 4;
  };
  const noIdle = { setTimeout: runAtOnce, clearTimeout: () => plain.push("cleared") };
  laterWhenIdle(noIdle as unknown as Window, () => plain.push("started"))();
  expect(plain).toEqual(["started", "cleared"]);
  expect(whenIdle({} as Window, () => plain.push("never"))).toBeInstanceOf(Function);
  expect(plain).not.toContain("never");
});

test("a page still loading waits for its load event, and a loaded one goes on at once", () => {
  const heard: string[] = [];
  const view = { addEventListener: (name: string) => heard.push(`listen ${name}`), removeEventListener: (name: string) => heard.push(`stop ${name}`) };
  const loading = afterLoad(view as unknown as Window, { readyState: "interactive" } as Document, () => heard.push("loaded"));
  loading();
  expect(heard).toEqual(["listen load", "stop load"]);
  afterLoad(view as unknown as Window, { readyState: "complete" } as Document, () => heard.push("loaded"));
  expect(heard.at(-1)).toBe("loaded");
});

test("the rest of a page is read from the document the page drew when its address still names it", async () => {
  const current = at(6);
  const named = reads({ [`en ${CURRENT}`]: current });
  expect(await addressedDocument(named.read, address(current))).toBe(current);
  expect(named.asked).toEqual([`en ${CURRENT}`]);
  const moved = { ...current, content: { ...current.content, units: {} } };
  const changed = reads({ [`en ${CURRENT}`]: moved, "en 6": current });
  expect(await addressedDocument(changed.read, address(current))).toBe(current);
  expect(changed.asked).toEqual([`en ${CURRENT}`, "en 6"]);
  for (const pages of ["crafts", "categories"]) expect(readFileSync(REST_ROUTE(pages), "utf8")).toContain("addressedDocument(serverDocumentReader(");
});

test("a category or craft page drawn a version behind reads the rest of that version, in its own language", async () => {
  const kept = at(5);
  const english = reads({ [`en ${CURRENT}`]: at(6), "en 5": kept });
  expect(await addressedDocument(english.read, address(kept))).toBe(kept);
  expect(english.asked).toEqual([`en ${CURRENT}`, "en 5"]);
  const hindi = at(5, "hi");
  const translated = reads({ [`hi ${CURRENT}`]: at(6, "hi"), "hi 5": hindi });
  expect(await addressedDocument(translated.read, address(hindi, "hi"))).toBe(hindi);
  expect(translated.asked).toEqual([`hi ${CURRENT}`, "hi 5"]);
});

test("a page drawn at a version that is gone reads the rest of its current version, in its own language", async () => {
  const dropped = at(5);
  const current = at(6);
  const english = reads({ [`en ${CURRENT}`]: current });
  expect(await addressedDocument(english.read, address(dropped))).toBe(current);
  expect(english.asked).toEqual([`en ${CURRENT}`, "en 5"]);
  const hindi = at(6, "hi");
  const translated = reads({ [`hi ${CURRENT}`]: hindi });
  expect(await addressedDocument(translated.read, address(at(5, "hi"), "hi"))).toBe(hindi);
  expect(translated.asked).toEqual([`hi ${CURRENT}`, "hi 5"]);
});

test("a rest that comes back in another language, or whose only version is earlier than the page's, is not found", async () => {
  const kept = at(5);
  const untranslated = reads({ [`hi ${CURRENT}`]: at(6), "hi 5": kept });
  expect(await addressedDocument(untranslated.read, address(at(5, "hi"), "hi"))).toBeNull();
  const english = reads({ [`hi ${CURRENT}`]: at(6) });
  expect(await addressedDocument(english.read, address(at(5, "hi"), "hi"))).toBeNull();
  expect(await addressedDocument(reads({ [`en ${CURRENT}`]: at(4) }).read, address(kept))).toBeNull();
  expect(await addressedDocument(reads({}).read, address(kept))).toBeNull();
});

test("a rest whose current version cannot be read fails, and never falls back to anything else", async () => {
  const failing: DocumentReader = async (language, version) => {
    if (version === null) throw new Error(`The monograph could not be read in ${language ?? "en"}: failed`);
    return null;
  };
  await expect(addressedDocument(failing, address(at(5)))).rejects.toThrow("could not be read");
});

function answering(status: number, body: unknown): { fetcher: RestFetcher; asked: string[] } {
  const asked: string[] = [];
  const fetcher: RestFetcher = async (src) => {
    asked.push(src);
    return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
  };
  return { fetcher, asked };
}

test("a page draws the rest its route sends at its own version or a later one, and never an earlier one", async () => {
  const golden = goldenDocument();
  const later = { ...golden, version: golden.version + 1 };
  const src = `/crafts/Kutch-Ajrakh/shell/v${golden.version}-${documentDigest(golden)}`;
  const same = answering(200, shellRest(golden));
  expect((await fetchedShellRest(same.fetcher, src, golden.version)).version).toBe(golden.version);
  expect(same.asked).toEqual([src]);
  expect((await fetchedShellRest(answering(200, shellRest(later)).fetcher, src, golden.version)).version).toBe(later.version);
  await expect(fetchedShellRest(answering(200, shellRest(golden)).fetcher, src, later.version)).rejects.toThrow(/another shape/);
  const generated = at(6);
  const drawn = (await fetchedDocumentRest(answering(200, documentRest(generated)).fetcher, "/categories/Textiles/shell/v5", 5)).document;
  expect(drawn.version).toBe(6);
  const mixed = { ...documentRest(generated), document: { ...documentRest(generated).document, version: 7 } };
  await expect(fetchedDocumentRest(answering(200, mixed).fetcher, "/categories/Textiles/shell/v5", 5)).rejects.toThrow(/another shape/);
  await expect(fetchedDocumentRest(answering(200, documentRest(at(4))).fetcher, "/categories/Textiles/shell/v5", 5)).rejects.toThrow(/another shape/);
});

test("a rest route that fails, or finds no version at all, leaves the page saying its rest could not be read", async () => {
  const golden = goldenDocument();
  const src = `/crafts/Kutch-Ajrakh/shell/v${golden.version}-${documentDigest(golden)}`;
  await expect(fetchedShellRest(answering(500, { detail: "failed" }).fetcher, src, golden.version)).rejects.toThrow(`${REST_UNREAD} (500)`);
  await expect(fetchedShellRest(answering(404, null).fetcher, src, golden.version)).rejects.toThrow(`${REST_UNREAD} (404)`);
  await expect(fetchedDocumentRest(answering(502, null).fetcher, "/categories/Textiles/shell/v5", 5)).rejects.toThrow(`${REST_UNREAD} (502)`);
});
