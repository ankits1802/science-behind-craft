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

export const DRAWING_CLASSES: readonly string[] = (
  "L air-o2 al ar arh ax bar base big cam ch-pic chel cl-base cl-blue cl-green cl-move cy-a cy-l cy-s cyc dam dax dbar desk " +
  "dgrid dhatch dipg dist dists dl dl2 dlab drips ev ext fig-svg fly fly-in fo foreign fr ft fw fz fz-b fz-bl fz-bp fz-dot " +
  "fz-dots fz-g fz-liq fz-o2 fz0 fz1 geo grid hatchpat hit ill ill-lab ill-line ill-num ill-say ill-sub in-box in-k in-land " +
  "indiafill indialo-line ink1 ink2 ink3 intl it kfocus kfocus-halo kl kv-ax kv-well kv-wl2 lab lab-m lab-p lab-r lab-riv " +
  "lab-v lab-w lab2 labs lc-bsvg lead liq liq-front liq-l ln lu m-b m-hl m-hls m-l mc mean mini minor mk mk-core mk-disc " +
  "mk-dot mkc mkr ml mol-g mol-ring move move-halo move-head mv new o2 ob off old op ovl ovl-halo ovl-line ox ox-blue ox-o2 " +
  "ox-wipe ox0 ox1 oxg pan-art ph pi pin pinkw pl rann rann-e rct rd rhead rhead-g ring ring-halo river river-arrow " +
  "river-flow river-halo route route-halo route-on rsgeo rt rx-svg saltpat sb scene sel-k sp states streams sup supply " +
  "supply-g svg-lab t t1 tall tb tdip tfill tg tlgeo top tox trend trend-h tw vat-svg vf-mini vg w-water w6 wa water " +
  "well-svg windia wkutch wkutch-h wl wland wp wrann wrann-e wstates zl-c zl-l zoom-link"
).split(" ");

const STYLE_PROPERTIES: ReadonlySet<string> = new Set(DRAWING_STYLE_PROPERTIES);
const KIT_CLASSES: ReadonlySet<string> = new Set(DRAWING_CLASSES);
const CLASS_ATTRIBUTES: ReadonlySet<string> = new Set(["class", "classname"]);
const REFERENCE_ATTRIBUTES: ReadonlySet<string> = new Set(["href", "xlink:href"]);
const REFUSED_ATTRIBUTES: ReadonlySet<string> = new Set(["cursor"]);
const EVENT_PREFIX = "on";
const STYLE_ATTRIBUTE = "style";
const LOCAL_REFERENCE = "#";
const CUSTOM_PROPERTY = /^--[a-z][a-z0-9-]*$/;
const STYLE_VALUE = /^[A-Za-z0-9\s.,%#()+_-]+$/;
const FOREIGN_LOAD = /url\((?!\s*(['"]?)#[\w.-]+\1\s*\))|image-set\(|cross-fade\(|(?<![\w-])(?:image|src)\(|\\/i;
const SCRIPTED = /javascript:|expression\(|@import/i;
const SVG_SIZE = /^\s*(\d+(?:\.\d+)?)\s*(px|%)?\s*$/;
const VIEW_BOX = /^\s*(-?\d+(?:\.\d+)?)[\s,]+(-?\d+(?:\.\d+)?)[\s,]+(\d+(?:\.\d+)?)[\s,]+(\d+(?:\.\d+)?)\s*$/;
const SHRINK = /\s*scale[XY]?\(\s*(\d*\.?\d+)\s*(?:[\s,]\s*(\d*\.?\d+)\s*)?\)\s*,?/iy;
const SVG_SIZES: ReadonlySet<string> = new Set(["width", "height"]);
const SHOWN_OVERFLOW: ReadonlySet<string> = new Set(["visible", "auto", "scroll"]);
const MOVED_ORIGIN: ReadonlySet<string> = new Set(["transform-origin", "transform-box"]);
const WHOLE_PERCENT = 100;
const WHOLE_SCALE = 1;

export const DRAWING_REFUSALS = {
  handler: "an attribute that runs no handler",
  script: "a value that runs no script",
  load: "a value that loads nothing from another address",
  reference: "a reference within the page",
  cursor: "no cursor",
  class: "only the classes the kit's own drawings carry",
  box: "an svg drawn within its box: its width and height at most its viewBox's or 100%, a transform that only shrinks it, nothing shown past its edge",
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
  if (CLASS_ATTRIBUTES.has(lowered) && !value.split(/\s+/).every((name) => !name || KIT_CLASSES.has(name))) return DRAWING_REFUSALS.class;
  return lowered === STYLE_ATTRIBUTE && !styleKept(value) ? DRAWING_REFUSALS.style : null;
}

export function svgViewBox(value: string | undefined): { width: number; height: number } | null {
  const found = VIEW_BOX.exec(value ?? "");
  if (!found) return null;
  const width = Number(found[3]);
  const height = Number(found[4]);
  return width > 0 && height > 0 ? { width, height } : null;
}

function within(value: string, bound: number | undefined): boolean {
  if (value.trim().toLowerCase() === "auto") return true;
  const size = SVG_SIZE.exec(value);
  if (!size) return false;
  const amount = Number(size[1]);
  if (size[2] === "%") return amount <= WHOLE_PERCENT;
  return bound !== undefined && amount <= bound;
}

function shrinks(transform: string): boolean {
  const text = transform.trim();
  if (!text || text.toLowerCase() === "none") return true;
  for (let at = 0; at < text.length; ) {
    SHRINK.lastIndex = at;
    const found = SHRINK.exec(text);
    if (!found || SHRINK.lastIndex === at) return false;
    if ([found[1], found[2]].some((factor) => factor !== undefined && Number(factor) > WHOLE_SCALE)) return false;
    at = SHRINK.lastIndex;
  }
  return true;
}

function unbounded(name: string, value: string, bounds: Readonly<Record<string, number>>): boolean {
  if (SVG_SIZES.has(name)) return !within(value, bounds[name]);
  if (name === "transform") return !shrinks(value);
  if (name === "overflow") return SHOWN_OVERFLOW.has(value.trim().toLowerCase());
  return MOVED_ORIGIN.has(name);
}

function declarations(name: string, value: string): [string, string][] {
  if (name !== STYLE_ATTRIBUTE) return [[name, value]];
  return value
    .split(";")
    .map((declaration): [string, string] => {
      const colon = declaration.indexOf(":");
      return colon < 0 ? [declaration.trim().toLowerCase(), ""] : [declaration.slice(0, colon).trim().toLowerCase(), declaration.slice(colon + 1).trim()];
    })
    .filter(([property]) => property);
}

export function svgBoxRefusal(attrs: Readonly<Record<string, string>>): DrawingRefusal | null {
  const given = Object.entries(attrs).map(([name, value]): [string, string] => [name.toLowerCase(), value]);
  const box = svgViewBox(given.find(([name]) => name === "viewbox")?.[1]);
  const bounds: Record<string, number> = box ? { width: box.width, height: box.height } : {};
  const outside = given.some(([name, value]) => declarations(name, value).some(([property, entry]) => unbounded(property, entry, bounds)));
  return outside ? DRAWING_REFUSALS.box : null;
}
