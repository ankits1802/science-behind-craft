import type { MonographComponent, MonographDocument, MonographUnit } from "../lib/monographDocument";

import { generatedDocument } from "./generatedMonographFixture";

export const PLAYER = "bagh-print/chemistry/reactions-step-by-step";
export const DIP = "bagh-print/chemistry/colour-after-each-stage";
export const MOLECULE = "bagh-print/chemistry/water-3d";
export const LAB = "bagh-print/chemistry/what-if-lab";
export const MORDANT = "bagh-print/chemistry/what-if-m01";
export const DYE = "bagh-print/chemistry/what-if-m03";
export const WATER_CID = 962;
export const REST_YAW_DEGREES = 23;

type Node = { tag: string; attrs?: Record<string, string>; children?: (Node | string)[] };
type Units = { add: (text: string) => string; all: Record<string, MonographUnit> };

const WATER: [string, number, number, number][] = [
  ["O", 0, -0.39, 0],
  ["H", 0.7572, 0.1953, 0],
  ["H", -0.7572, 0.1953, 0]
];
const BONDS: [number, number, number][] = [
  [0, 1, 1],
  [0, 2, 1]
];

function units(): Units {
  const all: Record<string, MonographUnit> = {};
  const add = (text: string) => {
    const ref = `u${5001 + Object.keys(all).length}`;
    all[ref] = { chapter: "chem", tag: "span", field: "CHEMISTRY", nodes: [text], claimIds: [] };
    return ref;
  };
  return { add, all };
}

const head = (u: Units, title: string) => ({ figure: null, number: u.add("Figure"), title: u.add(title), titleId: null, dek: null });

const rect = (fill: string, box: [number, number, number, number]): Node => ({
  tag: "rect",
  attrs: { x: String(box[0]), y: String(box[1]), width: String(box[2]), height: String(box[3]), fill, stroke: "var(--ink-2)", "stroke-width": "1.5" }
});

const piece = (token: string): Node => ({
  tag: "svg",
  attrs: { viewBox: "0 0 240 160", "aria-hidden": "true", focusable: "false" },
  children: [{ tag: "rect", attrs: { x: "0", y: "0", width: "240", height: "160", fill: "var(--sunk)" } }, rect(`var(${token})`, [40, 30, 160, 100])]
});

function step(u: Units, name: string, words: [string, string, string]) {
  const [kicker, heading, paragraph] = words;
  const lane = {
    part: "lane",
    label: "Species in this step",
    items: [
      { item: "species", swatch: "--dye-kut", name: [name], formula: null, state: [], cid: null },
      { item: "arrow", label: "complexation" },
      { item: "species", swatch: "clear", name: ["black"], formula: null, state: [], cid: null }
    ]
  };
  const none = { part: "none", unit: u.add("Named as the sources name it, without an equation.") };
  const text = { kicker: u.add(kicker), heading: u.add(heading), paragraphs: [u.add(paragraph)], bond: null, link: null, conditions: [], differs: null };
  return { name, text, chemistry: { parts: [lane, none] }, scene: null };
}

function player(u: Units) {
  const group = (on: number, fill: string): Node => ({ tag: "g", attrs: { "data-on": String(on), ...(on === 2 ? {} : { class: "off" }) }, children: [rect(fill, [40 + on * 80, 58, 64, 64])] });
  const scene: Node = {
    tag: "svg",
    attrs: { class: "scene", viewBox: "0 0 640 180", "aria-hidden": "true", focusable: "false" },
    children: [{ tag: "rect", attrs: { x: "0", y: "0", width: "640", height: "180", fill: "var(--sunk)" } }, group(1, "var(--dye-kut)"), group(2, "var(--dye-madder)")]
  };
  return {
    id: "rp-bagh-print",
    track: "reactions",
    head: head(u, "The reactions of Bagh Print, step by step"),
    current: 2,
    steps: [step(u, "Syahi", ["Redox", "Iron and acetic acid to iron acetate", "Syahi is made from scrap iron."]), step(u, "Madder bath", ["Complexation", "Alizarin and aluminium to red", "Alizarin binds aluminium."])],
    scenes: [scene],
    key: null,
    status: u.add("Alizarin and aluminium to red")
  };
}

function dip(u: Units) {
  return {
    id: "dip-bagh-print",
    head: head(u, "The colour of Bagh Print after each stage"),
    phase: u.add("Madder bath"),
    scene: piece("--dye-madder"),
    stripLabel: "The stages, in order",
    phases: [
      { pose: "harda", drawing: piece("--dye-harda"), kicker: u.add("Harda"), text: u.add("Yellow") },
      { pose: "madder-bath", drawing: piece("--dye-madder"), kicker: u.add("Madder bath"), text: u.add("Red where alum was printed") }
    ],
    dipAgain: "Dip again",
    status: u.add("Madder bath"),
    dipsLabel: u.add("The colour after each stage"),
    dips: ["--dye-harda", "--dye-madder"]
  };
}

function waterDrawing(): Node {
  const atom = (index: number, cx: string, cy: string, r: string, symbol: string): Node => ({
    tag: "g",
    attrs: { "data-a": String(index) },
    children: [
      { tag: "circle", attrs: { cx, cy, r, fill: `url(#ag-${symbol})`, stroke: "var(--mol-edge)", "stroke-width": "0.005" } },
      ...(symbol === "O" ? [{ tag: "text", attrs: { x: cx, y: cy, "font-size": "0.284", "text-anchor": "middle", "dominant-baseline": "central", fill: "var(--mol-letter)" }, children: ["O"] }] : [])
    ]
  });
  const bond = (index: number, d: string): Node => ({ tag: "path", attrs: { "data-b": String(index), d, stroke: "var(--mol-bond)", "stroke-width": "0.076", "stroke-linecap": "round" } });
  return {
    tag: "svg",
    attrs: { viewBox: "-1 -1 2 2", "aria-hidden": "true", focusable: "false" },
    children: [{ tag: "g", attrs: { class: "mol-g" }, children: [bond(0, "M0 0.27L0.48 -0.13"), bond(1, "M0 0.27L-0.48 -0.13"), atom(1, "0.48", "-0.13", "0.138", "H"), atom(2, "-0.48", "-0.13", "0.138", "H"), atom(0, "0", "0.27", "0.247", "O")] }]
  };
}

function molecule(u: Units) {
  const model = {
    key: `m${WATER_CID}`,
    cid: WATER_CID,
    yaw: 0.4,
    pitch: 0.3,
    name: "Water",
    dialLabel: "Turn the Water model",
    formula: ["H", { text: "2", style: "sub" }, "O"],
    atoms: "2 hydrogen and 1 oxygen atoms. Drag, or use the arrow keys, to turn it; plus and minus zoom.",
    note: "Its 3D conformer is PubChem's record.",
    drawing: waterDrawing(),
    geometry: { atoms: WATER, bonds: BONDS, radius: 1.38 }
  };
  const key = [
    { swatch: "--atom-h", label: "Hydrogen" },
    { swatch: "--atom-o", label: "Oxygen, O" },
    { swatch: null, label: "3D conformers computed by PubChem." }
  ];
  return { head: head(u, "Water in three dimensions"), molecules: [model], side: [{ tag: "p", style: "t-body-sm", unit: u.add("Water carries the dye into the cloth.") }], key };
}

function toggle(u: Units, experiment: string, options: [string, string, string][]) {
  return {
    experiment,
    questionId: `${experiment}-q`,
    question: u.add(`${options.map(([, label]) => label).join(" or ")}?`),
    options: options.map(([value, label, said]) => ({ value, label, heading: u.add(label), parts: [{ part: "text", unit: u.add(said) }] })),
    textParts: [],
    visualParts: []
  };
}

function lab(u: Units) {
  return {
    id: "lab-bagh-print",
    figure: "chem:1",
    number: u.add("Figure"),
    pickerLabel: "Choose an experiment",
    experiments: [
      { key: "m01", label: "Harda", toggle: { component: MORDANT } },
      { key: "m03", label: "Madder", toggle: { component: DYE } }
    ]
  };
}

function component(label: string, kind: string, title: string): MonographComponent {
  return { label, chapter: "chem", anchor: `#${label.replace(/\//g, "--")}`, kind, title, description: `${title}, composed from the page's own facts.`, field: "CHEMISTRY", fields: [], subjects: ["craft:Bagh-Print"] };
}

export function composedDocument(): MonographDocument {
  const document = generatedDocument();
  const u = units();
  const specs: Record<string, Record<string, unknown>> = {
    [PLAYER]: player(u),
    [DIP]: dip(u),
    [MOLECULE]: molecule(u),
    [MORDANT]: toggle(u, "m01", [
      ["m01", "Harda", "Harda gives the cloth its tannin."],
      ["m06", "Pomegranate rind", "Pomegranate rind can take the place of harda."]
    ]),
    [DYE]: toggle(u, "m03", [
      ["m03", "Madder", "Madder root holds alizarin."],
      ["m04", "Synthetic alizarin", "Synthetic alizarin now often stands in for madder."]
    ]),
    [LAB]: lab(u)
  };
  const components = [
    component(PLAYER, "reaction_player", "The reactions of Bagh Print"),
    component(DIP, "dip_player", "The colour after each stage"),
    component(MOLECULE, "molecule_3d", "Water in three dimensions"),
    component(MORDANT, "choice_toggle", "Harda or pomegranate rind"),
    component(DYE, "choice_toggle", "Madder or synthetic alizarin"),
    component(LAB, "experiment_lab", "What if, for Bagh Print")
  ];
  const at = document.content.layout.findIndex((entry) => entry.ref === "chemistry-1") + 1;
  const placed = components.map((found) => ({ chapter: "chem", kind: "component" as const, ref: found.label, within: null }));
  document.content.layout.splice(at, 0, ...placed);
  document.content.components.push(...components);
  Object.assign(document.content.units, u.all);
  Object.assign(document.specs, specs);
  document.content.data["mol-data"] = { [String(WATER_CID)]: { atoms: WATER, bonds: BONDS, R: 1.38, marks: [] } };
  return document;
}
