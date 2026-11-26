import { SANDBOX_CSP, SANDBOX_DATA_ELEMENT_ID, type SimulationValue } from "@/lib/explainerPlay";

export const FRAME_HEIGHT_MESSAGE = "kvFrameHeight";
export const FRAME_DEFAULT_HEIGHT = 360;
export const FRAME_MIN_HEIGHT = 120;
export const FRAME_MAX_HEIGHT = 1200;

export const FRAME_SIZER = [
  "new ResizeObserver(function () {",
  `parent.postMessage({ ${FRAME_HEIGHT_MESSAGE}: Math.ceil(document.documentElement.getBoundingClientRect().height) }, "*");`,
  "}).observe(document.documentElement);"
].join(" ");

export const FRAME_PEER_NAMES = ["RTCPeerConnection", "webkitRTCPeerConnection"] as const;
export const FRAME_NESTED = "iframe,frame,frameset,object,embed,portal,fencedframe";
export const FRAME_HOSTS = ["HTMLIFrameElement", "HTMLFrameElement", "HTMLObjectElement", "HTMLEmbedElement"] as const;

export const FRAME_GUARD = [
  "(function () {",
  `for (const name of ${JSON.stringify(FRAME_PEER_NAMES)}) delete window[name];`,
  "const none = { get: function () { return null; }, configurable: false };",
  `for (const type of ${JSON.stringify(FRAME_HOSTS)}) {`,
  "const host = window[type];",
  'if (host) for (const name of ["contentWindow", "contentDocument"]) if (name in host.prototype) Object.defineProperty(host.prototype, name, none);',
  "}",
  `const nested = ${JSON.stringify(FRAME_NESTED)};`,
  "new MutationObserver(function (changes) {",
  "for (const change of changes) for (const node of change.addedNodes) if (node.nodeType === 1) {",
  "if (node.matches(nested)) node.remove(); else for (const inner of node.querySelectorAll(nested)) inner.remove();",
  "}",
  "}).observe(document, { childList: true, subtree: true });",
  "})();"
].join(" ");

export const FRAME_REDUCED_MOTION = "data-reduced-motion";
export const FRAME_MOVING = "animate,animateTransform,animateMotion,set,marquee";
export const FRAME_STILLNESS = [
  "(function () {",
  "const root = document.documentElement;",
  `const flag = ${JSON.stringify(FRAME_REDUCED_MOTION)};`,
  'if (root.getAttribute(flag) !== "true" && !matchMedia("(prefers-reduced-motion: reduce)").matches) return;',
  'root.setAttribute(flag, "true");',
  "const settle = function (animation) { try { animation.finish(); } catch (error) { animation.cancel(); } return animation; };",
  "const settleAll = function () { if (document.getAnimations) for (const animation of document.getAnimations()) settle(animation); };",
  "const animate = Element.prototype.animate;",
  "if (animate) Element.prototype.animate = function () { return settle(animate.apply(this, arguments)); };",
  "if (window.Animation) {",
  'for (const name of ["play", "reverse", "updatePlaybackRate"]) Animation.prototype[name] = function () { settle(this); };',
  'for (const name of ["startTime", "currentTime", "playbackRate", "effect", "timeline"]) {',
  "const own = Object.getOwnPropertyDescriptor(Animation.prototype, name);",
  "if (own && own.set) Object.defineProperty(Animation.prototype, name, { get: own.get, set: function (value) { own.set.call(this, value); settle(this); }, configurable: true });",
  "}",
  "}",
  "const timing = window.AnimationEffect && AnimationEffect.prototype.updateTiming;",
  "if (timing) AnimationEffect.prototype.updateTiming = function () { timing.apply(this, arguments); settleAll(); };",
  "if (window.HTMLMarqueeElement) HTMLMarqueeElement.prototype.start = function () {};",
  "if (window.HTMLMediaElement) HTMLMediaElement.prototype.play = function () { this.pause(); return Promise.resolve(); };",
  "window.requestAnimationFrame = function () { return 0; };",
  "window.setInterval = function () { return 0; };",
  "const later = window.setTimeout;",
  "let timed = false;",
  'window.setTimeout = function (handler, delay) { if (timed || typeof handler !== "function") return 0; const given = Array.prototype.slice.call(arguments, 2); return later(function () { timed = true; try { handler.apply(null, given); } finally { timed = false; } }, delay); };',
  `const moving = ${JSON.stringify(FRAME_MOVING)};`,
  "const hold = function (node) {",
  "if (window.SVGAnimationElement && node instanceof SVGAnimationElement) node.remove();",
  "else if (window.HTMLMarqueeElement && node instanceof HTMLMarqueeElement) node.stop();",
  "else if (window.HTMLMediaElement && node instanceof HTMLMediaElement) { node.autoplay = false; node.pause(); }",
  "};",
  "new MutationObserver(function (changes) {",
  "for (const change of changes) {",
  'if (change.target === root && change.attributeName === flag && root.getAttribute(flag) !== "true") root.setAttribute(flag, "true");',
  "for (const node of change.addedNodes) if (node.nodeType === 1) { hold(node); for (const inner of node.querySelectorAll(moving)) hold(inner); }",
  "}",
  "settleAll();",
  "}).observe(document, { childList: true, subtree: true, attributes: true, characterData: true });",
  "})();"
].join(" ");

export const FRAME_IN_VIEW = "data-in-view";
export const FRAME_VIEW_EVENT = "kv-view";
export const FRAME_VIEW = [
  "(function () {",
  "const root = document.documentElement;",
  `const flag = ${JSON.stringify(FRAME_IN_VIEW)};`,
  "const tell = function (on) {",
  'const value = on ? "true" : "false";',
  "if (root.getAttribute(flag) === value) return;",
  "root.setAttribute(flag, value);",
  `document.dispatchEvent(new Event(${JSON.stringify(FRAME_VIEW_EVENT)}));`,
  "};",
  'root.setAttribute(flag, "false");',
  "if (!window.IntersectionObserver) { tell(true); return; }",
  "new IntersectionObserver(function (entries) { for (const entry of entries) tell(entry.isIntersecting); }).observe(root);",
  "})();"
].join(" ");

export function sandboxData(values: readonly Pick<SimulationValue, "key" | "value">[]): string {
  const data: Record<string, number> = {};
  for (const value of values) {
    if (!Number.isFinite(value.value)) throw new RangeError(`value ${value.key} is not a finite number`);
    if (Object.hasOwn(data, value.key)) throw new RangeError(`value ${value.key} is passed twice`);
    data[value.key] = value.value;
  }
  return JSON.stringify(data);
}

export type FrameLook = { tokens: Readonly<Record<string, string>>; reducedMotion: boolean };

export const FRAME_BASE_TOKENS = ["--sunk", "--ink-1", "--font-ui"] as const;
export const FRAME_STILL = "animation:none!important;transition:none!important;scroll-behavior:auto!important";
export const FRAME_MOTION_GUARD = [
  `html[data-reduced-motion="true"] *,html[data-reduced-motion="true"] *::before,html[data-reduced-motion="true"] *::after{${FRAME_STILL}}`,
  `@media (prefers-reduced-motion: reduce){*,*::before,*::after{${FRAME_STILL}}}`
].join("");

const TOKEN_NAME = /^--[a-z0-9-]+$/;
const UNSAFE_VALUE = /[<>{};\\]/;
const USED_TOKEN = /var\(\s*(--[a-z0-9-]+)/g;

export function frameTokenNames(html: string): string[] {
  return [...new Set([...FRAME_BASE_TOKENS, ...[...html.matchAll(USED_TOKEN)].map((found) => found[1])])];
}

export function frameLookStyle(look: FrameLook): string {
  const declared = Object.entries(look.tokens)
    .filter(([name, value]) => TOKEN_NAME.test(name) && value.trim() !== "" && !UNSAFE_VALUE.test(value))
    .map(([name, value]) => `${name}:${value.trim()}`);
  return `:root{${declared.join(";")}}body{margin:0;background:var(--sunk);color:var(--ink-1);font-family:var(--font-ui)}${FRAME_MOTION_GUARD}`;
}

function frameIsStill(look: FrameLook | null): boolean {
  return look === null || look.reducedMotion;
}

export type FramePieces = { csp: string; head: string };

export const NO_PIECES: FramePieces = { csp: SANDBOX_CSP, head: "" };

export function sandboxDocument(html: string, values: readonly Pick<SimulationValue, "key" | "value">[], look: FrameLook | null = null, pieces: FramePieces = NO_PIECES): string {
  return [
    frameIsStill(look) ? `<!doctype html><html lang="en" ${FRAME_REDUCED_MOTION}="true"><head>` : '<!doctype html><html lang="en"><head>',
    `<meta http-equiv="Content-Security-Policy" content="${pieces.csp}">`,
    '<meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1">',
    `<script type="application/json" id="${SANDBOX_DATA_ELEMENT_ID}">${sandboxData(values)}</script>`,
    `<script>${FRAME_GUARD}</script>`,
    `<script>${FRAME_SIZER}</script>`,
    `<script>${FRAME_STILLNESS}</script>`,
    `<script>${FRAME_VIEW}</script>`,
    pieces.head,
    `<style>${look ? frameLookStyle(look) : FRAME_MOTION_GUARD}</style>`,
    `</head><body>${html}</body></html>`
  ].join("");
}

export function readFrameLook(names: readonly string[], read: (name: string) => string, reducedMotion: boolean): FrameLook {
  const tokens: Record<string, string> = {};
  const wanted = [...names];
  for (let at = 0; at < wanted.length; at += 1) {
    const value = read(wanted[at]).trim();
    if (!value) continue;
    tokens[wanted[at]] = value;
    for (const found of value.matchAll(USED_TOKEN)) if (!wanted.includes(found[1])) wanted.push(found[1]);
  }
  return { tokens, reducedMotion };
}

export function ownFrameHeight(event: { source: unknown; data: unknown }, frame: unknown): number | null {
  if (frame === null || frame === undefined || event.source !== frame) return null;
  return frameHeightFrom(event.data);
}

export function frameHeightFrom(message: unknown): number | null {
  if (typeof message !== "object" || message === null || Array.isArray(message)) return null;
  const keys = Object.keys(message);
  if (keys.length !== 1 || keys[0] !== FRAME_HEIGHT_MESSAGE) return null;
  const height = (message as Record<string, unknown>)[FRAME_HEIGHT_MESSAGE];
  if (typeof height !== "number" || !Number.isFinite(height)) return null;
  return Math.min(FRAME_MAX_HEIGHT, Math.max(FRAME_MIN_HEIGHT, Math.ceil(height)));
}
