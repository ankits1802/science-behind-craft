import type { MonographComponent, MonographDocument, MonographNode, MonographUnit } from "../lib/monographDocument";

import { templateDocument } from "./templateMonographFixture";

export const WIDE = "bagh-print/pictures/wide";
export const BLEED = "bagh-print/pictures/bleed";
export const COLUMN = "bagh-print/pictures/column";
export const MARGIN = "bagh-print/pictures/margin";
export const IRON = "bagh-print/chemistry/iron-black";
export const VAT = "bagh-print/chemistry/indigo-vat";
export const KILN = "bagh-print/chemistry/kiln";
export const PULL = "chem-quote";
export const SIDE = "chem-side";
export const PICTURE_WIDTH = 1600;
export const PICTURE_HEIGHT = 1200;

type Layout = MonographDocument["content"]["layout"][number];
export type Entry = { ref: string; chapter: string; order: number; role: string; size?: string; crop?: { x: number; y: number; width: number; height: number } };

const PICTURES: readonly (readonly [string, string])[] = [
  [WIDE, "Cloth washed in running water"],
  [BLEED, "Printed lengths drying across the field"],
  [COLUMN, "A dyer at the washing step"],
  [MARGIN, "Blocks pressed by hand"]
];

const span = (text: string): MonographUnit => ({ chapter: "opening", tag: "span", field: null, nodes: [text], claimIds: [] });
const cited = (text: string, key: string, sources: string[]): MonographNode => ({ m: "s", c: [`${text} `, { m: "cite", key, g: sources, c: ["here."] }] });
const chem = (tag: string, nodes: MonographNode[]): MonographUnit => ({ chapter: "chem", tag, field: null, nodes, claimIds: [] });
const at = (chapter: string, ref: string, kind: Layout["kind"] = "unit", within: string | null = null): Layout => ({ chapter, kind, ref, within });

function component(label: string, chapter: string, kind: string, title: string, description: string): MonographComponent {
  return { label, chapter, anchor: `#${label.replace(/\//g, "--")}`, kind, title, description, field: "PROCESS", fields: [], subjects: ["craft:Bagh-Print"] };
}

function plate(index: number): Record<string, unknown> {
  return {
    setting: "figure",
    picture: { src: `https://upload.wikimedia.org/wikipedia/commons/a/ab/P${index}.jpg`, width: PICTURE_WIDTH, height: PICTURE_HEIGHT, alt: `Picture P${index}`, loading: null, fetchPriority: null, decoding: null },
    figure: { classes: ["plate"], crop: null, captions: [{ unit: `u91${index}1`, look: false }], credit: `u91${index}2` },
    row: null,
    pull: null,
    opener: null,
    masthead: null
  };
}

export function layoutEntries(document: MonographDocument): Entry[] {
  return [...(document.content.data["page-layout"] as { entries: Entry[] }).entries];
}

export function withLayout(document: MonographDocument, entries: readonly Entry[]): MonographDocument {
  document.content.data = { ...document.content.data, "page-layout": { schemaVersion: 1, subjectKind: "craft", subjectSlug: "Bagh-Print", version: 1, entries } };
  return document;
}

export function sizedDocument(crop: Entry["crop"] = undefined): MonographDocument {
  const document = templateDocument();
  PICTURES.forEach(([label, caption], index) => {
    document.content.components.push(component(label, "made", "picture_plate", caption, `A picture for Bagh Print: ${caption}.`));
    document.specs[label] = plate(index);
    document.content.units[`u91${index}1`] = span(caption);
    document.content.units[`u91${index}2`] = span("Photo: A. Printer, CC BY-SA 4.0, via Wikimedia Commons");
  });
  const layout = document.content.layout;
  const head = layout.findIndex((entry) => entry.ref === "chapter-made");
  const placed = PICTURES.flatMap(([label], index) => [at("made", label, "component"), at("made", `u91${index}1`, "unit", label), at("made", `u91${index}2`, "unit", label)]);
  document.content.layout = [...layout.slice(0, head + 1), ...placed, ...layout.slice(head + 1)];
  return withLayout(document, [
    { ref: WIDE, chapter: "made", order: 1, role: "FIGURE", size: "WIDE" },
    { ref: BLEED, chapter: "made", order: 2, role: "FIGURE", size: "BLEED" },
    { ref: COLUMN, chapter: "made", order: 3, role: "FIGURE", size: "COLUMN", ...(crop ? { crop } : {}) },
    { ref: MARGIN, chapter: "made", order: 4, role: "SIDEBAR" }
  ]);
}

const CHEM_UNITS: Record<string, MonographUnit> = {
  "chem-vat-h": chem("h3", ["The vat"]),
  "chem-vat": chem("p", [cited("Indigo is reduced to leucoindigo in the pit", "chem-vat", ["g2"])]),
  "chem-iron-h": chem("h3", ["Black"]),
  "chem-iron": chem("p", [cited("Iron and tannin print the black outline", "chem-iron", ["g3"])]),
  [PULL]: chem("p", [cited("The printers say the river makes the colour", PULL, ["g4"])]),
  [SIDE]: chem("p", [cited("A second bath deepens the red", SIDE, ["g2"])])
};

export function proseDocument(): MonographDocument {
  const document = templateDocument();
  Object.assign(document.content.units, CHEM_UNITS);
  document.content.components.push(
    component(IRON, "chem", "diagram", "Iron and tannin black", "Iron and tannin print the black."),
    component(VAT, "chem", "diagram", "The indigo pit", "Leucoindigo turns blue in the air."),
    component(KILN, "chem", "diagram", "A kiln drawing", "A kiln fired with wood.")
  );
  const layout = document.content.layout;
  const head = layout.findIndex((entry) => entry.ref === "chapter-chem");
  const named = [at("chem", IRON, "component"), at("chem", VAT, "component"), at("chem", KILN, "component"), at("chem", PULL), at("chem", SIDE)];
  const prose = ["chem-vat-h", "chem-vat", "chem-iron-h", "chem-iron"].map((ref) => at("chem", ref));
  document.content.layout = [...layout.slice(0, head + 1), ...named, ...layout.slice(head + 1, head + 2), ...prose, ...layout.slice(head + 2)];
  return withLayout(document, [
    { ref: IRON, chapter: "chem", order: 1, role: "FIGURE" },
    { ref: VAT, chapter: "chem", order: 2, role: "FIGURE" },
    { ref: KILN, chapter: "chem", order: 3, role: "FIGURE" },
    { ref: PULL, chapter: "chem", order: 4, role: "PULL_QUOTE" },
    { ref: SIDE, chapter: "chem", order: 5, role: "SIDEBAR" }
  ]);
}
