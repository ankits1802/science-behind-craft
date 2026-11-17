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

export function sandboxData(values: readonly Pick<SimulationValue, "key" | "value">[]): string {
  const data: Record<string, number> = {};
  for (const value of values) {
    if (!Number.isFinite(value.value)) throw new RangeError(`value ${value.key} is not a finite number`);
    if (Object.hasOwn(data, value.key)) throw new RangeError(`value ${value.key} is passed twice`);
    data[value.key] = value.value;
  }
  return JSON.stringify(data);
}

export function sandboxDocument(html: string, values: readonly Pick<SimulationValue, "key" | "value">[]): string {
  return [
    '<!doctype html><html lang="en"><head>',
    `<meta http-equiv="Content-Security-Policy" content="${SANDBOX_CSP}">`,
    '<meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1">',
    `<script type="application/json" id="${SANDBOX_DATA_ELEMENT_ID}">${sandboxData(values)}</script>`,
    `<script>${FRAME_GUARD}</script>`,
    `<script>${FRAME_SIZER}</script>`,
    `</head><body>${html}</body></html>`
  ].join("");
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
