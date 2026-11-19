import type { Page } from "@playwright/test";

export type StyleRecord = Record<string, Record<string, string>>;
export type StyleDifference = { node: string; property: string; approved: string; rendered: string };
export type FontReport = { userAgent: string; pixelRatio: number; faces: string[] };

const PROPERTIES = [
  "font-family",
  "font-size",
  "font-weight",
  "font-style",
  "font-variation-settings",
  "font-optical-sizing",
  "font-feature-settings",
  "font-kerning",
  "font-synthesis",
  "letter-spacing",
  "word-spacing",
  "line-height",
  "text-wrap",
  "text-rendering",
  "white-space",
  "max-width",
  "padding-inline-start",
  "padding-inline-end",
  "margin-inline-start",
  "margin-block-start",
  "color",
  "transform",
  "-webkit-font-smoothing",
  "-webkit-text-size-adjust",
  "font-variant-ligatures",
  "font-variant-numeric",
  "background-color",
  "opacity"
];
const LAYER_PROPERTIES = ["transform", "will-change", "opacity", "filter", "backdrop-filter", "contain", "isolation", "mix-blend-mode", "position", "overflow", "z-index", "-webkit-font-smoothing", "text-rendering"];
const MAX_NODES = 40;

export async function elementStyles(page: Page, id: string): Promise<StyleRecord> {
  return page.evaluate(
    ({ target, properties, max }) => {
      const root = document.getElementById(target);
      if (!root) return {};
      const host = document.getElementById("kv-main")?.getBoundingClientRect().top ?? 0;
      const nodes = [root, ...root.querySelectorAll("*")].slice(0, max);
      return Object.fromEntries(
        nodes.map((node, index) => {
          const style = getComputedStyle(node);
          const box = node.getBoundingClientRect();
          const classes = typeof node.className === "string" ? node.className.trim().split(/\s+/).filter(Boolean).join(".") : "";
          const record: Record<string, string> = Object.fromEntries(properties.map((name) => [name, style.getPropertyValue(name)]));
          record["box-x"] = box.left.toFixed(2);
          record["box-width"] = box.width.toFixed(2);
          record["box-height"] = box.height.toFixed(2);
          record["box-y-in-main"] = (box.top - host).toFixed(2);
          record["box-y-fraction"] = ((((box.top + window.scrollY) % 1) + 1) % 1).toFixed(2);
          return [`${index}:${node.tagName.toLowerCase()}${classes ? `.${classes}` : ""}`, record];
        })
      );
    },
    { target: id, properties: PROPERTIES, max: MAX_NODES }
  );
}

export function styleDifferences(approved: StyleRecord, rendered: StyleRecord): StyleDifference[] {
  const nodes = [...new Set([...Object.keys(approved), ...Object.keys(rendered)])];
  return nodes.flatMap((node) => nodeDifferences(node, approved[node], rendered[node]));
}

function nodeDifferences(node: string, approved?: Record<string, string>, rendered?: Record<string, string>): StyleDifference[] {
  if (!approved || !rendered) return [{ node, property: "node", approved: approved ? "present" : "missing", rendered: rendered ? "present" : "missing" }];
  return Object.keys(approved)
    .filter((property) => approved[property] !== rendered[property])
    .map((property) => ({ node, property, approved: approved[property], rendered: rendered[property] }));
}

export async function fontReport(page: Page): Promise<FontReport> {
  return page.evaluate(() => ({
    userAgent: navigator.userAgent,
    pixelRatio: window.devicePixelRatio,
    faces: [...document.fonts]
      .filter((face) => face.status === "loaded")
      .map((face) => `${face.family} ${face.style} ${face.weight} ${face.stretch} ${face.unicodeRange.slice(0, 24)}`)
  }));
}

const GOOGLE_FONT_CSS = "https://fonts.googleapis.com/css2**";

export async function selfHostedFaces(page: Page): Promise<string> {
  return page.evaluate(() =>
    [...document.styleSheets]
      .flatMap((sheet) => {
        try {
          return [...sheet.cssRules]
            .filter((rule) => rule instanceof CSSFontFaceRule)
            .map((rule) => rule.cssText.replace(/url\("?([^")]+)"?\)/g, (_, url: string) => `url("${new URL(url, sheet.href ?? location.href).href}")`));
        } catch {
          return [];
        }
      })
      .join("\n")
  );
}

export async function servedFaces(page: Page, faces: string): Promise<void> {
  await page.route(GOOGLE_FONT_CSS, (route) => route.fulfill({ status: 200, contentType: "text/css", body: faces }));
}

export async function chapterOffsets(page: Page): Promise<Record<string, string>> {
  return page.evaluate(() => {
    const host = document.getElementById("kv-main")?.getBoundingClientRect().top ?? 0;
    return Object.fromEntries([...document.querySelectorAll("#kv-main [id]")].map((element) => [element.id, (element.getBoundingClientRect().top - host).toFixed(2)]));
  });
}

export async function ancestorLayers(page: Page, id: string): Promise<string[]> {
  return page.evaluate(
    ({ target, properties }) => {
      const chain: string[] = [];
      for (let node = document.getElementById(target)?.parentElement; node; node = node.parentElement) {
        const style = getComputedStyle(node);
        const set = properties.map((name) => `${name}=${style.getPropertyValue(name)}`).join(" ");
        const classes = typeof node.className === "string" ? node.className.trim().split(/\s+/).filter(Boolean).slice(0, 3).join(".") : "";
        chain.push(`${node.tagName.toLowerCase()}${node.id ? `#${node.id}` : ""}${classes ? `.${classes}` : ""} ${set}`);
      }
      return chain;
    },
    { target: id, properties: LAYER_PROPERTIES }
  );
}
