import { readFileSync } from "node:fs";
import { join } from "node:path";

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { AuthProvider } from "../components/AuthProvider";
import { MonographPage } from "../components/monograph/MonographPage";
import { ThemeProvider } from "../components/ThemeProvider";
import { parseKindFixtures } from "../lib/kindFixtures";
import type { MonographComponent, MonographDocument } from "../lib/monographDocument";

import { composedDocument, PLAYER } from "./composedInteractivesFixture";
import { FRONTEND } from "./moduleGraph";
import { PRIMITIVE_CSS } from "./primitivesPage";

export const STAGES = "bastar-dhokra/process/lost-wax-stages";
export const LONG_NAME = "Ferrous-tannate-complex-of-the-printed-syahi-and-the-harda-tannin-held-on-the-cotton";
export const LONG_FORMULA = "C76H52O46Fe2C76H52O46Fe2C76H52O46";
export const LONG_STATE = "Dissolved-in-the-boiling-madder-bath-water-of-the-river";

const READ = (...parts: string[]) => readFileSync(join(FRONTEND, ...parts), "utf8");
export const KIT_CSS = READ("public", "monographs", "kit", "monograph.css");
export const KIT_JS = READ("public", "monographs", "kit", "monograph.js");
const PAGE_CSS = READ("components", "monograph", "documentPage.css");
const ARTKIT_CSS = READ("components", "artkit", "artkit.css");
const STAGE_FIXTURE = parseKindFixtures({ fixtures: [JSON.parse(READ("..", "backend", "app", "data", "kind_fixtures", "stage_player.json"))] })[0];

type Spec = Record<string, unknown>;
type Step = { scene: unknown; chemistry: { parts: { items?: Spec[] }[] } };

const renumbered = (value: unknown): unknown => JSON.parse(JSON.stringify(value).replace(/"u0(\d{3})"/g, '"u7$1"'));

function adder(document: MonographDocument) {
  let next = 6001;
  return (text: string) => {
    const ref = `u${next++}`;
    document.content.units[ref] = { chapter: "chem", tag: "span", field: "CHEMISTRY", nodes: [text], claimIds: [] };
    return ref;
  };
}

function species(add: (text: string) => string, role: string, name: string, material?: string, breaks = false): Spec {
  return { part: "species", role, label: add(name), ...(material ? { material } : {}), ...(breaks ? { breaks: true } : {}) };
}

function reacting(document: MonographDocument, add: (text: string) => string): void {
  const player = document.specs[PLAYER] as { steps: Step[]; scenes: unknown[] };
  player.scenes = [];
  player.steps[0].scene = { where: add("Syahi"), art: { parts: [species(add, "reactant", "iron", "--dye-kut", true), species(add, "reagent", "oxygen"), species(add, "product", "iron acetate")], motion: "react" } };
  player.steps[1].scene = { where: add("Madder bath"), art: { parts: [species(add, "reactant", "alizarin", "--dye-madder"), species(add, "reagent", "aluminium"), species(add, "product", "red")], motion: "react" } };
}

function lengthened(document: MonographDocument): void {
  const player = document.specs[PLAYER] as { steps: Step[] };
  for (const step of player.steps) {
    const first = step.chemistry.parts[0].items?.[0];
    if (first) Object.assign(first, { name: [LONG_NAME], formula: [LONG_FORMULA], state: [LONG_STATE] });
  }
}

function staged(document: MonographDocument): void {
  for (const [ref, unit] of Object.entries(STAGE_FIXTURE.units)) document.content.units[ref.replace(/^u0/, "u7")] = { chapter: "chem", tag: "span", field: "PROCESS", nodes: [unit.text], claimIds: [] };
  document.specs[STAGES] = renumbered(STAGE_FIXTURE.spec) as Spec;
  const component: MonographComponent = { label: STAGES, chapter: "chem", anchor: "#bastar-dhokra--process--lost-wax-stages", kind: "stage_player", title: STAGE_FIXTURE.title, description: STAGE_FIXTURE.description, field: "PROCESS", fields: [], subjects: [] };
  document.content.components.push(component);
  const at = document.content.layout.findIndex((entry) => entry.ref === PLAYER) + 1;
  document.content.layout.splice(at, 0, { chapter: "chem", kind: "component", ref: STAGES, within: null });
}

export function playersDocument({ long = false }: { long?: boolean } = {}): MonographDocument {
  const document = composedDocument();
  const add = adder(document);
  reacting(document, add);
  if (long) lengthened(document);
  staged(document);
  return document;
}

export type Motion = "allowed" | "system" | "page";

export function playersHtml(motion: Motion, document: MonographDocument = playersDocument()): string {
  const body = renderToStaticMarkup(createElement(AuthProvider, null, createElement(ThemeProvider, null, createElement(MonographPage, { document }))));
  const head = `<meta charset="utf-8"><style>${PRIMITIVE_CSS}</style><style>${KIT_CSS}</style><style>${PAGE_CSS}</style><style>${ARTKIT_CSS}</style>`;
  const switched = motion === "page" ? ' data-reduced-motion="true"' : "";
  return `<!doctype html><html lang="en" data-theme="light"${switched}><head>${head}</head><body>${body}</body></html>`;
}
