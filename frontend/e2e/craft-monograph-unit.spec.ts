import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { RSC_HEADER } from "next/dist/client/components/app-router-headers";
import { getPathMatch } from "next/dist/shared/lib/router/utils/path-match";

import { CRAFT_MONOGRAPHS, ROUTER_REQUEST_HEADER, cameByRouter, isCraftMonograph } from "../lib/craftMonographs";
import nextConfig from "../next.config";

const PUBLIC = join(__dirname, "..", "public");
const AJRAKH = "/crafts/Kutch-Ajrakh";

async function rewriteFor(path: string) {
  const rewrites = await nextConfig.rewrites!();
  const rules = Array.isArray(rewrites) ? rewrites : [...(rewrites.beforeFiles ?? []), ...(rewrites.afterFiles ?? []), ...(rewrites.fallback ?? [])];
  return rules.find((entry) => getPathMatch(entry.source, { strict: true, removeUnnamedParams: true })(path) !== false) ?? null;
}

async function servedFile(path: string): Promise<string | null> {
  return (await rewriteFor(path))?.destination ?? null;
}

function monograph(): string {
  return readFileSync(join(PUBLIC, CRAFT_MONOGRAPHS["Kutch-Ajrakh"]), "utf8");
}

test("the Kutch Ajrakh craft page serves the monograph as built, to every reader", async () => {
  const served = await servedFile(AJRAKH);
  expect(served).toBe("/monographs/kutch-ajrakh/index.html");
  expect(monograph()).toContain("<title>KalaVigyan · Kutch Ajrakh</title>");
});

test("the app's router is answered by the app, never by the static file, so its prefetch is never a 404", async () => {
  expect(ROUTER_REQUEST_HEADER).toBe(RSC_HEADER);
  expect((await rewriteFor(AJRAKH))?.missing).toEqual([{ type: "header", key: RSC_HEADER }]);
});

test("the app hands a monograph over to a full page load only when its router brought the reader", () => {
  expect(isCraftMonograph("Kutch-Ajrakh")).toBe(true);
  expect(isCraftMonograph("Kutch-Bandhani")).toBe(false);
  expect(isCraftMonograph("constructor")).toBe(false);
  expect(cameByRouter("/crafts", AJRAKH)).toBe(true);
  expect(cameByRouter(AJRAKH, AJRAKH)).toBe(false);
  expect(cameByRouter(null, AJRAKH)).toBe(false);
});

test("every other craft address keeps the craft page", async () => {
  for (const path of ["/crafts/Kutch-Bandhani", "/crafts/Bagru-Hand-Block-Prints", `${AJRAKH}/v1`, "/crafts", "/ask"]) {
    expect(await servedFile(path), path).toBeNull();
  }
});

test("every picture of the monograph is served beside it", () => {
  const pictures = [...monograph().matchAll(/<img[^>]*\ssrc="([^"]+)"/g)].map((found) => found[1]).filter((src) => !src.startsWith("data:"));
  expect(pictures.length).toBeGreaterThan(0);
  for (const src of pictures) {
    expect(src, src).toMatch(/^\/monographs\/kutch-ajrakh\/img\//);
    expect(existsSync(join(PUBLIC, src)), src).toBe(true);
  }
});

test("each Ask next question opens the ask page for Kutch Ajrakh", () => {
  const asks = [...monograph().matchAll(/<a href="([^"]+)" data-ask="([^"]+)">/g)];
  expect(asks).toHaveLength(6);
  for (const [, href, question] of asks) {
    const url = new URL(href.replaceAll("&amp;", "&"), "https://reader.test");
    expect(url.pathname).toBe("/ask");
    expect(url.searchParams.get("q")).toBe(question);
    expect(url.searchParams.get("craft")).toBe("Kutch-Ajrakh");
  }
});
