import type { CodedDam, CodedRiverPath } from "@/components/map/codedStillCut";
import { codedValues, type CodedFigureSpec, type CodedLibrary } from "@/lib/componentSpecsScienceCoded";
import { SANDBOX_ATTRIBUTE } from "@/lib/explainerPlay";
import { sandboxDocument, type FrameLook, type FramePieces } from "@/lib/sandboxFrame";

export const WORDS_ELEMENT_ID = "kv-words";
export const FILMS_ELEMENT_ID = "kv-films";
export const MAP_ELEMENT_ID = "kv-map";
export const DAM_SHARE = 0.012;
export const CODED_SANDBOX = SANDBOX_ATTRIBUTE;
export const LIBRARY_PATHS: Readonly<Record<CodedLibrary, string>> = {
  d3: "/monographs/kit/vendor/d3-7.9.2.min.js",
  three: "/monographs/kit/vendor/three-0.187.0.min.js"
};

export type MapBounds = { west: number; east: number; south: number; north: number };
export type MapHome = { lgd: number; d: string; x: number; y: number };
export type MapBase = {
  bounds: MapBounds;
  width: number;
  padding: number;
  viewBox: string;
  outline: string;
  rann: string;
  relief: { step: number; d: string }[];
  rivers: string[];
  states: string | null;
  districts: string | null;
  homes: MapHome[];
  named?: { rivers: CodedRiverPath[]; dams: CodedDam[] };
};

const RELIEF_STEPS = [1, 2, 3, 4, 5, 6, 7];

export const FRAME_KIT_SHEET = [
  "body{font-family:var(--font-ui);font-size:14px;line-height:1.45}",
  "svg{max-width:100%}",
  "button{font:inherit;min-height:44px;padding:0 16px;border:1px solid var(--rule-strong);border-radius:4px;background:var(--raised);color:var(--ink-1);cursor:pointer}",
  'button[aria-pressed="true"]{background:var(--indigo);border-color:var(--indigo);color:var(--on-indigo)}',
  ":focus-visible{outline:2px solid var(--indigo);outline-offset:3px}",
  '[role="status"]{color:var(--ink-2)}',
  ".kv-map-land{fill:var(--map-land);stroke:none}",
  ".kv-map-outline{fill:none;stroke:var(--map-border-intl);stroke-width:1.2;vector-effect:non-scaling-stroke}",
  ".kv-map-state{fill:none;stroke:var(--map-border-state);stroke-width:0.8;vector-effect:non-scaling-stroke}",
  ".kv-map-district{fill:none;stroke:var(--map-border-district);stroke-width:0.5;vector-effect:non-scaling-stroke}",
  ".kv-map-river{fill:none;stroke:var(--map-river);stroke-width:1;vector-effect:non-scaling-stroke}",
  ".kv-map-salt{fill:var(--map-salt);stroke:none}",
  ".kv-map-home{fill:none;stroke:var(--terracotta);stroke-width:1.5;vector-effect:non-scaling-stroke}",
  ".kv-map-river-named{fill:none;stroke:var(--map-river);stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke}",
  ".kv-map-dam{fill:var(--map-label);stroke:var(--map-label-halo);stroke-width:1;vector-effect:non-scaling-stroke}",
  ...RELIEF_STEPS.map((step) => `.kv-map-relief-${step}{fill:var(--elevation-${step});stroke:none}`)
].join("");

const FILLED = `[data-unit],[data-unit-label],[data-film]`;

export const FRAME_FILLS = [
  "(function () {",
  "const read = function (id) { const found = document.getElementById(id); return found ? JSON.parse(found.textContent) : {}; };",
  `const words = read(${JSON.stringify(WORDS_ELEMENT_ID)});`,
  `const films = read(${JSON.stringify(FILMS_ELEMENT_ID)});`,
  "const own = function (held, key) { return Object.prototype.hasOwnProperty.call(held, key) ? held[key] : null; };",
  "const fill = function (node) {",
  'if (node.hasAttribute("data-unit")) { const said = own(words, node.getAttribute("data-unit")); if (said !== null && node.textContent !== said) node.textContent = said; }',
  'if (node.hasAttribute("data-unit-label")) { const said = own(words, node.getAttribute("data-unit-label")); if (said !== null) node.setAttribute("aria-label", said); }',
  'if (node.hasAttribute("data-film")) { const src = own(films, node.getAttribute("data-film")); if (src !== null && node.getAttribute("src") !== src) node.setAttribute("src", src); }',
  "};",
  `const fillAll = function (root) { if (root.nodeType !== 1) return; if (root.matches(${JSON.stringify(FILLED)})) fill(root); for (const inner of root.querySelectorAll(${JSON.stringify(FILLED)})) fill(inner); };`,
  "new MutationObserver(function (changes) {",
  'for (const change of changes) { if (change.type === "attributes") fill(change.target); else for (const node of change.addedNodes) fillAll(node); }',
  '}).observe(document, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-unit", "data-unit-label", "data-film"] });',
  "})();"
].join(" ");

export const FRAME_MAP = [
  "(function () {",
  `const source = document.getElementById(${JSON.stringify(MAP_ELEMENT_ID)});`,
  "if (!source) return;",
  "const base = JSON.parse(source.textContent);",
  "const named = base.named || { rivers: [], dams: [] };",
  'const NS = "http://www.w3.org/2000/svg";',
  "const across = Math.cos(((base.bounds.south + base.bounds.north) / 2) * Math.PI / 180);",
  "const unit = (base.width - base.padding * 2) / ((base.bounds.east - base.bounds.west) * across);",
  "const project = function (longitude, latitude) { return { x: base.padding + (longitude - base.bounds.west) * across * unit, y: base.padding + (base.bounds.north - latitude) * unit }; };",
  "const box = function (west, south, east, north, margin) { const a = project(west, north); const b = project(east, south); const m = margin || 0; return [a.x - m, a.y - m, b.x - a.x + 2 * m, b.y - a.y + 2 * m].map(function (n) { return Math.round(n * 10) / 10; }).join(\" \"); };",
  'const shape = function (d, name) { const path = document.createElementNS(NS, "path"); path.setAttribute("d", d); path.setAttribute("class", name); return path; };',
  `const dam = function (found, width) { const size = width * ${DAM_SHARE}; const mark = document.createElementNS(NS, "rect"); mark.setAttribute("x", found.x - size); mark.setAttribute("y", found.y - size / 3); mark.setAttribute("width", size * 2); mark.setAttribute("height", (size * 2) / 3); mark.setAttribute("class", "kv-map-dam"); return mark; };`,
  "const drawn = function (svg) {",
  "const view = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width ? svg.viewBox.baseVal.width : base.width;",
  'const group = document.createElementNS(NS, "g"); group.setAttribute("class", "kv-map-base"); group.setAttribute("aria-hidden", "true");',
  'group.appendChild(shape(base.outline, "kv-map-land"));',
  'for (const band of base.relief) group.appendChild(shape(band.d, "kv-map-relief-" + band.step));',
  'for (const d of base.rivers) group.appendChild(shape(d, "kv-map-river"));',
  'if (base.districts) group.appendChild(shape(base.districts, "kv-map-district"));',
  'if (base.states) group.appendChild(shape(base.states, "kv-map-state"));',
  'for (const home of base.homes) group.appendChild(shape(home.d, "kv-map-home"));',
  'for (const river of named.rivers) group.appendChild(shape(river.d, "kv-map-river-named"));',
  "for (const found of named.dams) group.appendChild(dam(found, view));",
  'group.appendChild(shape(base.rann, "kv-map-salt"));',
  'group.appendChild(shape(base.outline, "kv-map-outline"));',
  "return group;",
  "};",
  'const kept = function (svg) { const first = svg.firstElementChild; return first !== null && first.getAttribute("class") === "kv-map-base" && first.lastElementChild !== null && first.lastElementChild.getAttribute("d") === base.outline; };',
  'const lay = function (svg) { if (kept(svg)) return; for (const old of svg.querySelectorAll(":scope > .kv-map-base")) old.remove(); svg.insertBefore(drawn(svg), svg.firstChild); };',
  'const all = function () { for (const svg of document.querySelectorAll("svg[data-map]")) lay(svg); };',
  "const frozen = function (rows) { return Object.freeze(rows.map(function (row) { return Object.freeze(Object.assign({}, row)); })); };",
  "window.kvMap = Object.freeze({ viewBox: base.viewBox, project: project, box: box, places: frozen(base.homes.map(function (home) { return { lgd: home.lgd, x: home.x, y: home.y }; })), rivers: frozen(named.rivers), dams: frozen(named.dams) });",
  "new MutationObserver(all).observe(document, { childList: true, subtree: true });",
  "})();"
].join(" ");

export function libraryUrls(origin: string, libraries: readonly CodedLibrary[]): string[] {
  return libraries.map((name) => `${origin}${LIBRARY_PATHS[name]}`);
}

export function codedFrameCsp(origin: string, figure: Pick<CodedFigureSpec, "libraries" | "films">): string {
  const scripts = ["'unsafe-inline'", ...libraryUrls(origin, figure.libraries ?? [])].join(" ");
  const films = (figure.films ?? []).map((film) => `${origin}${film.src}`);
  const media = films.length ? films.join(" ") : "'none'";
  return `default-src 'none'; script-src ${scripts}; style-src 'unsafe-inline'; img-src data:; media-src ${media}; webrtc 'block'`;
}

function jsonElement(id: string, value: unknown): string {
  return `<script type="application/json" id="${id}">${JSON.stringify(value).replace(/</g, "\\u003c")}</script>`;
}

export type CodedFrameAsk = { origin: string; figure: CodedFigureSpec; words: Readonly<Record<string, string>>; base: MapBase | null };

export function codedFramePieces(ask: CodedFrameAsk): FramePieces {
  const films = Object.fromEntries((ask.figure.films ?? []).map((film) => [film.key, `${ask.origin}${film.src}`]));
  const head = [
    jsonElement(WORDS_ELEMENT_ID, ask.words),
    jsonElement(FILMS_ELEMENT_ID, films),
    ask.base ? jsonElement(MAP_ELEMENT_ID, ask.base) : "",
    `<script>${FRAME_FILLS}</script>`,
    ask.base ? `<script>${FRAME_MAP}</script>` : "",
    ...libraryUrls(ask.origin, ask.figure.libraries ?? []).map((url) => `<script src="${url}"></script>`)
  ];
  return { csp: codedFrameCsp(ask.origin, ask.figure), head: head.join("") };
}

export function codedFrameHtml(figure: Pick<CodedFigureSpec, "code">): string {
  return `<style>${FRAME_KIT_SHEET}</style>${figure.code}`;
}

export function codedFrameDocument(ask: CodedFrameAsk, look: FrameLook | null): string {
  return sandboxDocument(codedFrameHtml(ask.figure), codedValues(ask.figure), look, codedFramePieces(ask));
}
