import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { NEAR_MARGIN, nearBlocksLoaded, nearSignal, whenNear, type NearEntry, type NearObserverMaker } from "@/components/answer/nearBlock";
import { AuthProvider } from "@/components/AuthProvider";
import { COMPONENT_VIEWS } from "@/components/monograph/componentViews";
import { MapLayerView } from "@/components/monograph/kinds/general/MapLayerView";
import { TimelineMapDeclaredView } from "@/components/monograph/kinds/general/TimelineMapDeclaredView";
import { NEAR_RESERVE_LABEL } from "@/components/monograph/kinds/nearViews";
import { WhyHereView } from "@/components/monograph/kinds/place/WhyHereView";
import { GeneratorView } from "@/components/monograph/kinds/tools/GeneratorView";
import type { ComponentView, ComponentViewProps } from "@/lib/componentViewContract";
import type { KindFixture } from "@/lib/kindFixtures";
import { WHY_HERE_KIND } from "@/lib/placeGround";

import { clientBoundaries, dynamicImports, heavyChains, PACKAGE, reachedStyles } from "./clientGraph";
import { filedKindFixtures } from "./phoneFixturePage";

test.beforeAll(() => nearBlocksLoaded());

const REPO = join(__dirname, "..", "..");
const NEAR_VIEWS = "components/monograph/kinds/nearViews.tsx";
const NEAR_KIT_PLAY = "components/artkit/NearKitPlay.tsx";
const HEAVY_PACKAGES = [`${PACKAGE}3dmol`, `${PACKAGE}katex`, `${PACKAGE}@elevenlabs/client`];
const CRAFT_ROUTE = ["app/layout.tsx", "app/(reading)/layout.tsx", "app/(reading)/crafts/[slug]/page.tsx"];
const REST_CHUNKS = ["components/monograph/DeferredShell.tsx", "components/monograph/DeferredDocument.tsx"];
const GENERATED_ID = /\b(id|for|aria-labelledby|aria-describedby|aria-controls|href|clip-path|mask|fill|filter)="[^"]*"/g;
const AT_REST_HIDDEN = /^<div data-kv-near=""><[^>]*style="[^"]*opacity:\s*0[;"]/;

const fixtures = filedKindFixtures();
const fixture = (label: string) => fixtures.find((found) => found.label === label) as KindFixture;

function fixtureProps(found: KindFixture): ComponentViewProps {
  const component = { label: found.label, chapter: "k1", anchor: "#k", kind: found.kind, title: found.title, description: found.description, field: found.field, fields: [], subjects: [] };
  const text = (ref: string) => found.units[ref]?.text ?? "";
  return { component, spec: found.spec, unitRefs: Object.keys(found.units), renderUnit: text, unitText: text, renderComponent: () => null };
}

function propsOf(kind: string, label: string, spec: Record<string, unknown>, unitRefs: string[]): ComponentViewProps {
  const component = { label, chapter: "c", anchor: "#c", kind, title: label, description: label, field: "OVERVIEW", fields: [], subjects: [] };
  return { component, spec, unitRefs, renderUnit: (ref) => `[${ref}]`, unitText: (ref) => `[${ref}]`, renderComponent: () => null };
}

const readJson = (...parts: string[]) => JSON.parse(readFileSync(join(REPO, ...parts), "utf8")) as Record<string, unknown>;
const ground = readJson("shared", "place.ground.golden.json");
const generator = readJson("backend", "app", "data", "monographs", "Kutch-Ajrakh", "specs", "kutch-ajrakh__overview__watch-it-being-made.json");

const HEAVY_CASES: { kind: string; eager: ComponentView; props: ComponentViewProps }[] = [
  { kind: WHY_HERE_KIND, eager: WhyHereView, props: propsOf(WHY_HERE_KIND, "ground-fixture/geography/why-here", { ground, notes: [] }, []) },
  { kind: "map_layer", eager: MapLayerView, props: fixtureProps(fixture("bidriware/history/centres")) },
  { kind: "timeline_map", eager: TimelineMapDeclaredView, props: fixtureProps(fixture("bidriware/history/where-bidri-was-made")) },
  { kind: "generator", eager: GeneratorView, props: propsOf("generator", "kutch-ajrakh/overview/watch-it-being-made", generator, []) }
];

function drawn(view: ComponentView, props: ComponentViewProps): string {
  return renderToStaticMarkup(createElement(AuthProvider, null, createElement(() => view(props)))).replace(GENERATED_ID, '$1=""');
}

for (const { kind, eager, props } of HEAVY_CASES) {
  test(`a ${kind} is drawn whole and still at first paint, in the holder that loads its code near the viewport`, () => {
    const still = drawn(eager, props);
    const near = drawn(COMPONENT_VIEWS[kind] as ComponentView, props);
    expect(still.length).toBeGreaterThan(200);
    expect(near).toBe(`<div data-kv-near="">${still}</div>`);
    expect(near).not.toMatch(AT_REST_HIDDEN);
    expect(near).not.toContain(NEAR_RESERVE_LABEL);
  });
}

test("on the client a heavy kind holds a figure-shaped reserve until it nears the viewport", () => {
  const view = COMPONENT_VIEWS[WHY_HERE_KIND] as ComponentView;
  const scope = globalThis as { window?: unknown };
  scope.window = globalThis;
  try {
    const held = renderToStaticMarkup(createElement(() => view(HEAVY_CASES[0].props)));
    expect(held).toContain('data-skeleton="chart"');
    expect(held).toContain(NEAR_RESERVE_LABEL);
    expect(held).not.toContain("<svg");
  } finally {
    delete scope.window;
  }
});

function fakeObserver(): { make: NearObserverMaker; seen: (entries: NearEntry[]) => void; watched: Element[]; margins: string[]; stopped: () => number } {
  const watched: Element[] = [];
  const margins: string[] = [];
  let stops = 0;
  let react: (entries: readonly NearEntry[]) => void = () => undefined;
  const make: NearObserverMaker = (seen, options) => {
    react = seen;
    margins.push(options.rootMargin ?? "");
    return { observe: (element) => void watched.push(element), disconnect: () => void (stops += 1) };
  };
  return { make, seen: (entries) => react(entries), watched, margins, stopped: () => stops };
}

test("a holder reaches the viewport once, a screen and a half ahead, and stops watching", () => {
  const observer = fakeObserver();
  const reached: string[] = [];
  const holder = {} as Element;
  const stop = whenNear(holder, () => reached.push("near"), observer.make);
  expect(observer.watched).toEqual([holder]);
  expect(observer.margins).toEqual([NEAR_MARGIN]);
  observer.seen([{ isIntersecting: false }]);
  expect(reached).toEqual([]);
  observer.seen([{ isIntersecting: false }, { isIntersecting: true }]);
  expect(reached).toEqual(["near"]);
  expect(observer.stopped()).toBe(1);
  stop();
  expect(observer.stopped()).toBe(2);
  const without: string[] = [];
  whenNear(null, () => without.push("at once"), observer.make);
  whenNear(holder, () => without.push("no observer"), null);
  expect(without).toEqual(["at once", "no observer"]);
});

test("a near signal resolves when it is reached, and starts reached on the server", async () => {
  const waiting = nearSignal(false);
  let settled = false;
  void waiting.promise.then(() => (settled = true));
  await Promise.resolve();
  expect([waiting.reached, settled]).toEqual([false, false]);
  waiting.reach();
  await waiting.promise;
  expect([waiting.reached, settled]).toEqual([true, true]);
  const served = nearSignal(true);
  await served.promise;
  expect(served.reached).toBe(true);
});

test("the craft page reaches a heavy view or library only through an import made near the viewport", () => {
  const nearModules = dynamicImports(NEAR_VIEWS);
  expect(nearModules).toEqual([
    "components/monograph/kinds/place/WhyHereView.tsx",
    "components/monograph/kinds/general/MapLayerView.tsx",
    "components/monograph/kinds/general/TimelineMapDeclaredView.tsx",
    "components/monograph/kinds/tools/ExplainerView.tsx",
    "components/monograph/kinds/tools/QuizView.tsx",
    "components/monograph/kinds/tools/AskNextView.tsx",
    "components/monograph/kinds/tools/LanguageSwitchView.tsx",
    "components/monograph/kinds/tools/ReadingLevelView.tsx",
    "components/monograph/kinds/tools/GeneratorView.tsx"
  ]);
  expect(dynamicImports(NEAR_KIT_PLAY)).toEqual(["components/artkit/KitPlay.tsx"]);
  const nearLoaded = [...nearModules, ...dynamicImports(NEAR_KIT_PLAY)];
  const heavy = (node: string) => nearLoaded.includes(node) || HEAVY_PACKAGES.includes(node);
  const entries = [...clientBoundaries(CRAFT_ROUTE), ...REST_CHUNKS];
  expect(entries).toContain("components/monograph/BundleView.tsx");
  expect(entries).toContain("components/monograph/DeferredShellSlot.tsx");
  const chains = entries.flatMap((entry) => heavyChains(entry, heavy)).map((chain) => chain.join(" > "));
  expect(chains, chains.join("\n")).toEqual([]);
});

test("a registry that imports a heavy view outright is named with the imports that reach it", () => {
  const nearModules = dynamicImports(NEAR_VIEWS);
  const chains = heavyChains("e2e/heavyImportFixture.ts", (node) => nearModules.includes(node));
  expect(chains).toEqual([["e2e/heavyImportFixture.ts", "components/monograph/kinds/general/TimelineMapDeclaredView.tsx"]]);
});

test("every stylesheet a heavy view brings is on the page before its code, so its still state is styled at first paint", () => {
  const drawnFirst = new Set([...reachedStyles(NEAR_VIEWS), ...reachedStyles("components/monograph/BundleView.tsx")]);
  expect(drawnFirst.has("components/map/place-context/placeContext.css")).toBe(true);
  const late = dynamicImports(NEAR_VIEWS).flatMap((view) => reachedStyles(view).filter((sheet) => !drawnFirst.has(sheet)).map((sheet) => `${view} > ${sheet}`));
  expect(late).toEqual([]);
});

test("a composed kit figure draws its panels and its Play at rest, and the Play's code waits for the viewport", () => {
  const kit = fixture("bidriware/process/white-to-black-in-the-bath");
  const html = drawn(COMPONENT_VIEWS.diagram as ComponentView, fixtureProps(kit));
  expect(html).toContain('<ol class="kv-kit-panels">');
  expect(html).toContain('<div data-kv-near=""><div class="kv-kit-play">');
  expect(html.match(/>Play</g)).toHaveLength(1);
  expect(html).not.toContain("data-playing");
});
