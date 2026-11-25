import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { AuthProvider } from "../components/AuthProvider";
import { COMPONENT_VIEWS } from "../components/monograph/componentViews";
import { MonographPage } from "../components/monograph/MonographPage";
import { ThemeProvider } from "../components/ThemeProvider";
import { KIT_PART_NAMES } from "../lib/artKit";
import { KIT_SCENE_KINDS, kitSceneShape } from "../lib/componentSpecsKitScene";
import { dipPlayerShape, reactionPlayerShape, stagePlayerShape } from "../lib/componentSpecsSciencePlayers";
import type { ComponentView } from "../lib/componentViewContract";
import { parseKindFixtures, type KindFixture } from "../lib/kindFixtures";
import type { MonographComponent, MonographContent, MonographDocument } from "../lib/monographDocument";
import { parseShape, ShapeError } from "../lib/shape";

import { composedDocument, MADDER_SAID, PLAYER } from "./composedInteractivesFixture";
import { FRONTEND } from "./moduleGraph";
import { AJRAKH_DIR } from "./monographMarkup";
import { PRIMITIVE_CSS, primitivesPage } from "./primitivesPage";

type Spec = Record<string, unknown>;
type Case = { kind: string; label: string; spec: Spec; text: (ref: string) => string };

const READ = (...parts: string[]) => readFileSync(join(FRONTEND, ...parts), "utf8");
const KIT_CSS = READ("public", "monographs", "kit", "monograph.css");
const KIT_JS = READ("public", "monographs", "kit", "monograph.js");
const PAGE_CSS = READ("components", "monograph", "documentPage.css");
const ARTKIT_CSS = READ("components", "artkit", "artkit.css");
const FIXTURES = join(FRONTEND, "..", "backend", "app", "data", "kind_fixtures");
const AJRAKH = JSON.parse(readFileSync(join(AJRAKH_DIR, "content.json"), "utf8")) as MonographContent;
const WIDTHS = [360, 1440] as const;
const SWITCHES = ["system", "page"] as const;
const BATH = { part: "bath", vessel: "pot", piece: "--dye-bidri-black", label: "u0901" };
const VESSEL = { part: "piece", shape: "vessel", material: "--dye-bidri-white", inlay: { motif: "lines", material: "--dye-bidri-silver" }, label: "u0902" };
const LABELS: Readonly<Record<string, string>> = { u0901: "Boiling fort earth and ammonium chloride", u0902: "Zinc-white alloy, inlaid with silver" };

const fixture = (name: string): KindFixture => parseKindFixtures({ fixtures: [JSON.parse(readFileSync(join(FIXTURES, `${name}.json`), "utf8"))] })[0];
const texts = (found: KindFixture) => (ref: string) => found.units[ref]?.text ?? LABELS[ref] ?? "";
const fromFixture = (found: KindFixture, spec: Spec = found.spec): Case => ({ kind: found.kind, label: found.label, spec, text: texts(found) });

const TOGGLE = fixture("choice_toggle");
const CARD = fixture("label_card");
const KIT: readonly Case[] = [
  fromFixture(fixture("reaction_player")),
  fromFixture(fixture("dip_player")),
  fromFixture(fixture("stage_player")),
  fromFixture(TOGGLE, { ...TOGGLE.spec, visualParts: [{ part: "stage", drawing: { parts: [BATH, VESSEL] }, note: null, noteHook: null }] }),
  fromFixture(CARD, { ...CARD.spec, seal: { parts: [VESSEL] } })
];
const FREE_LABELS = [
  "shared/chemistry/indigo-reduction-player",
  "shared/chemistry/indigo-vat-dip",
  "kutch-ajrakh/process/cloth-after-each-stage",
  "kutch-ajrakh/chemistry/what-if-indigo-vat",
  "kutch-ajrakh/policy/gi-registration-card"
];
const SCENE_NAMES: Readonly<Record<string, string[]>> = {
  reaction_player: ["r1", "r2"],
  dip_player: ["scene", "ph0", "ph1", "ph2"],
  stage_player: ["stage"],
  choice_toggle: ["v0"],
  label_card: ["seal"]
};

function drawn({ kind, label, spec, text }: Case): string {
  const view = COMPONENT_VIEWS[kind] as ComponentView;
  const component: MonographComponent = { label, chapter: "k1", anchor: "#k", kind, title: label, description: "", field: "CHEMISTRY", fields: [], subjects: [] };
  return renderToStaticMarkup(createElement(() => view({ component, spec, unitRefs: [], renderUnit: text, unitText: text, renderComponent: () => null })));
}

function ajrakh(label: string): Case {
  const kind = AJRAKH.components.find((found) => found.label === label)?.kind ?? "";
  const spec = JSON.parse(readFileSync(join(AJRAKH_DIR, "specs", `${label.replaceAll("/", "__")}.json`), "utf8")) as Spec;
  return { kind, label, spec, text: (ref) => `[${ref}]` };
}

function partLabels(value: unknown): string[] {
  if (Array.isArray(value)) return value.flatMap(partLabels);
  if (typeof value !== "object" || value === null) return [];
  const record = value as Record<string, unknown>;
  const own = typeof record.part === "string" && (KIT_PART_NAMES as readonly string[]).includes(record.part) && typeof record.label === "string" ? [record.label] : [];
  return [...own, ...Object.values(record).flatMap(partLabels)];
}

function kitPage(): string {
  const [reaction, dip, stage, toggle, card] = KIT.map(drawn);
  return primitivesPage(`<style>${KIT_CSS}</style><style>${ARTKIT_CSS}</style><main style="padding-inline:16px"><div class="bx-chem">${reaction}${dip}</div><div class="bx-pt">${stage}${toggle}${card}</div></main>`);
}

function kitDocument(): MonographDocument {
  const document = composedDocument();
  const add = (ref: string, text: string) => {
    document.content.units[ref] = { chapter: "chem", tag: "span", field: "CHEMISTRY", nodes: [text], claimIds: [] };
    return ref;
  };
  const player = document.specs[PLAYER] as { steps: Spec[]; scenes: unknown[] };
  player.scenes = [];
  player.steps[0].scene = { where: add("u5901", "Syahi"), art: { parts: [{ ...BATH, piece: "--dye-kut", label: add("u5902", "Syahi in its pot") }], motion: "dip" } };
  player.steps[1].scene = { where: add("u5903", "Madder bath"), art: { parts: [{ part: "cloth", form: "swatch", material: "--dye-madder", label: add("u5904", MADDER_SAID) }], motion: "take" } };
  return document;
}

async function generated(page: Page, motion: "allowed" | (typeof SWITCHES)[number]): Promise<void> {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: motion === "system" ? "reduce" : "no-preference" });
  const switched = motion === "page" ? ' data-reduced-motion="true"' : "";
  const body = renderToStaticMarkup(createElement(AuthProvider, null, createElement(ThemeProvider, null, createElement(MonographPage, { document: kitDocument() }))));
  const head = `<meta charset="utf-8"><style>${PRIMITIVE_CSS}</style><style>${KIT_CSS}</style><style>${PAGE_CSS}</style><style>${ARTKIT_CSS}</style>`;
  await page.setContent(`<!doctype html><html lang="en" data-theme="light"${switched}><head>${head}</head><body>${body}</body></html>`, { waitUntil: "domcontentloaded" });
  await page.addScriptTag({ content: KIT_JS });
  await expect(page.locator("figure.rp .rp-text")).toHaveAttribute("style", /min-height/);
}

test("the five kinds that take a kit scene are the backend's", () => {
  expect([...KIT_SCENE_KINDS].sort()).toEqual(KIT.map((found) => found.kind).sort());
});

for (const found of KIT) {
  test(`a ${found.kind} draws its kit scenes from the kit's parts, each part named by its cited label`, () => {
    const html = drawn(found);
    const names = [...html.matchAll(/data-kit-scene="([^"]+)"/g)].map((match) => match[1]);
    expect(names).toEqual(SCENE_NAMES[found.kind]);
    expect(html).toContain('class="kv-kit-defs"');
    expect(html).toContain('class="kv-kit-key"');
    for (const ref of partLabels(found.spec)) expect(html, ref).toContain(found.text(ref));
    expect(html).not.toContain("data-playing");
  });
}

test("each kind keeps its free drawing, and Kutch Ajrakh's authored players draw no kit part", () => {
  const free = [...FREE_LABELS.map(ajrakh), fromFixture(CARD)];
  expect(free.map((found) => found.kind)).toEqual(["reaction_player", "dip_player", "stage_player", "choice_toggle", "label_card", "label_card"]);
  for (const found of free) {
    const html = drawn(found);
    expect(html.length, found.label).toBeGreaterThan(0);
    for (const kit of ["data-kit-scene", "kv-kit-defs", "kv-kit-scene-key", "data-kit-part"]) expect(html, `${found.label} ${kit}`).not.toContain(kit);
  }
});

test("a slot tells a kit scene from a drawing by its parts, and a scene at rest names no motion", () => {
  expect(parseShape(dipPlayerShape, fixture("dip_player").spec).phases[0].drawing).toMatchObject({ motion: "dip" });
  expect(parseShape(reactionPlayerShape, fixture("reaction_player").spec).steps[0].scene?.whereIcon).toBeUndefined();
  const stage = fixture("stage_player").spec;
  expect(() => parseShape(stagePlayerShape, { ...stage, drawing: { parts: [{ part: "cloth", form: "swatch", material: "--dye-madder", label: "u0902" }], motion: "take" } })).toThrow(ShapeError);
  expect(() => parseShape(kitSceneShape, { parts: [BATH, BATH, VESSEL, VESSEL] })).toThrow(ShapeError);
  expect(() => parseShape(kitSceneShape, { parts: [{ ...BATH, piece: "--ink-1" }] })).toThrow(ShapeError);
});

for (const width of WIDTHS) {
  test(`every kit scene and its key fit ${width}px in light and dark, labels at 12px or more`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    for (const theme of ["light", "dark"]) {
      await page.setContent(kitPage().replace('<html lang="en" ', `<html lang="en" data-theme="${theme}" `));
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), theme).toBe(true);
      const scenes = await page.evaluate(() => [...document.querySelectorAll("svg.kv-kit-scene")].filter((node) => node.getClientRects().length > 0).map((node) => node.getBoundingClientRect().width));
      expect(scenes).toHaveLength(8);
      expect(Math.min(...scenes), theme).toBeGreaterThanOrEqual(60);
      const sizes = await page.evaluate(() => [...document.querySelectorAll(".kv-kit-key")].map((node) => parseFloat(getComputedStyle(node).fontSize)));
      expect(Math.min(...sizes), theme).toBeGreaterThanOrEqual(12);
    }
  });
}

test("a dip phase's key sits in the strip's text column on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 900 });
  await page.setContent(kitPage());
  const placed = await page.evaluate(() =>
    [...document.querySelectorAll(".vs")].map((phase) => {
      const art = phase.querySelector("svg.vf-mini")!.getBoundingClientRect();
      const key = phase.querySelector(".kv-kit-scene-key")!.getBoundingClientRect();
      return key.left >= art.right - 1 && key.width > 0;
    })
  );
  expect(placed).toEqual([true, true, true]);
});

test("a reaction step and a dip phase play their part's own motion when the reader shows them", async ({ page }) => {
  await generated(page, "allowed");
  const player = page.locator("figure.rp");
  await player.locator(".rp-rail button").first().click();
  const moving = player.locator('.rx[data-i="1"] [data-kit-move]');
  expect(await moving.evaluate((node) => [node.hasAttribute("data-playing"), getComputedStyle(node).animationName])).toEqual([true, "kv-dip"]);
  const dip = page.locator("figure.vat");
  await dip.evaluate((node) => node.scrollIntoView({ block: "center" }));
  await expect(dip.locator(".vat-dip")).toHaveAttribute("aria-pressed", "true");
  await expect.poll(() => dip.locator(".vat-scene [data-kit-move][data-playing]").count(), { intervals: [50] }).toBe(1);
});

for (const motion of SWITCHES) {
  test(`under the ${motion} reduced-motion switch a kit scene shows its state at once and nothing moves`, async ({ page }) => {
    await generated(page, motion);
    const player = page.locator("figure.rp");
    await player.locator(".rp-rail button").first().click();
    await expect(player).toHaveAttribute("data-step", "1");
    await expect(player.locator('.rx[data-i="1"]')).toBeVisible();
    const dip = page.locator("figure.vat");
    await dip.locator(".vat-dip").click();
    await expect(dip.locator(".vs").first()).toHaveAttribute("aria-current", "step");
    await expect(page.locator("[data-kit-move][data-playing]")).toHaveCount(0);
    const names = await page.evaluate(() => [...document.querySelectorAll("[data-kit-move]")].map((node) => getComputedStyle(node).animationName));
    expect(new Set(names)).toEqual(new Set(["none"]));
  });
}
