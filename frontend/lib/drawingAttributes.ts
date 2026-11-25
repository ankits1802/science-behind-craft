export const DRAWING_STYLE_PROPERTIES = [
  "alignment-baseline",
  "baseline-shift",
  "clip-path",
  "clip-rule",
  "color",
  "color-interpolation",
  "color-interpolation-filters",
  "direction",
  "display",
  "dominant-baseline",
  "fill",
  "fill-opacity",
  "fill-rule",
  "flood-color",
  "flood-opacity",
  "font-family",
  "font-size",
  "font-stretch",
  "font-style",
  "font-variant",
  "font-weight",
  "image-rendering",
  "isolation",
  "letter-spacing",
  "lighting-color",
  "mix-blend-mode",
  "opacity",
  "paint-order",
  "pointer-events",
  "shape-rendering",
  "stop-color",
  "stop-opacity",
  "stroke",
  "stroke-dasharray",
  "stroke-dashoffset",
  "stroke-linecap",
  "stroke-linejoin",
  "stroke-miterlimit",
  "stroke-opacity",
  "stroke-width",
  "text-anchor",
  "text-decoration",
  "text-rendering",
  "transform",
  "transform-box",
  "transform-origin",
  "unicode-bidi",
  "vector-effect",
  "visibility",
  "white-space",
  "word-spacing",
  "writing-mode"
] as const;

const STYLE_PROPERTIES: ReadonlySet<string> = new Set(DRAWING_STYLE_PROPERTIES);
const REFERENCE_ATTRIBUTES: ReadonlySet<string> = new Set(["href", "xlink:href"]);
const REFUSED_ATTRIBUTES: ReadonlySet<string> = new Set(["cursor"]);
const EVENT_PREFIX = "on";
const STYLE_ATTRIBUTE = "style";
const LOCAL_REFERENCE = "#";
const CUSTOM_PROPERTY = /^--[a-z][a-z0-9-]*$/;
const STYLE_VALUE = /^[A-Za-z0-9\s.,%#()+_-]+$/;
const FOREIGN_LOAD = /url\((?!\s*(['"]?)#[\w.-]+\1\s*\))|image-set\(|cross-fade\(|(?<![\w-])(?:image|src)\(|\\/i;
const SCRIPTED = /javascript:|expression\(|@import/i;

export const DRAWING_REFUSALS = {
  handler: "an attribute that runs no handler",
  script: "a value that runs no script",
  load: "a value that loads nothing from another address",
  reference: "a reference within the page",
  cursor: "no cursor",
  style: "a style of paint, stroke, opacity, transform, text, display and custom properties with token or number values"
} as const;

export type DrawingRefusal = (typeof DRAWING_REFUSALS)[keyof typeof DRAWING_REFUSALS];

function folded(value: string): string {
  return value.replace(/\s/g, "");
}

export function loadsNothing(value: string): boolean {
  return !FOREIGN_LOAD.test(value) && !SCRIPTED.test(folded(value));
}

export function styleKept(style: string): boolean {
  return style
    .split(";")
    .filter((declaration) => declaration.trim())
    .every((declaration) => {
      const colon = declaration.indexOf(":");
      const name = declaration.slice(0, colon).trim().toLowerCase();
      const value = declaration.slice(colon + 1).trim();
      if (colon < 0 || !name || !value) return false;
      return (STYLE_PROPERTIES.has(name) || CUSTOM_PROPERTY.test(name)) && STYLE_VALUE.test(value);
    });
}

export function drawingAttributeRefusal(name: string, value: string): DrawingRefusal | null {
  const lowered = name.toLowerCase();
  if (lowered.startsWith(EVENT_PREFIX)) return DRAWING_REFUSALS.handler;
  if (SCRIPTED.test(folded(value))) return DRAWING_REFUSALS.script;
  if (FOREIGN_LOAD.test(value)) return DRAWING_REFUSALS.load;
  if (REFERENCE_ATTRIBUTES.has(lowered) && !value.startsWith(LOCAL_REFERENCE)) return DRAWING_REFUSALS.reference;
  if (REFUSED_ATTRIBUTES.has(lowered)) return DRAWING_REFUSALS.cursor;
  return lowered === STYLE_ATTRIBUTE && !styleKept(value) ? DRAWING_REFUSALS.style : null;
}
