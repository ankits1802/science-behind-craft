import type { SvgNode } from "@/lib/componentSpecsScienceParts";
import { svgViewBox } from "@/lib/drawingAttributes";

export const WHERE_ICON_UNITS_MOST = 32;
export const WHERE_VIGNETTE_CLASS = "vg";

const DECORATIVE = { "aria-hidden": "true" } as const;

type ViewSize = { width: number; height: number };

function viewSize(node: SvgNode): ViewSize | null {
  return svgViewBox(node.attrs?.viewBox);
}

function classes(node: SvgNode): string[] {
  return (node.attrs?.class ?? "").split(/\s+/).filter(Boolean);
}

function withClasses(attrs: Record<string, string>, names: readonly string[]): Record<string, string> {
  const rest = Object.fromEntries(Object.entries(attrs).filter(([name]) => name !== "class"));
  return names.length ? { ...rest, class: names.join(" ") } : rest;
}

function iconAtItsOwnSize(node: SvgNode, size: ViewSize): SvgNode {
  const kept = classes(node).filter((name) => name !== WHERE_VIGNETTE_CLASS);
  const attrs = { ...withClasses(node.attrs ?? {}, kept), ...DECORATIVE, width: String(size.width), height: String(size.height) };
  return { ...node, attrs };
}

function asVignette(node: SvgNode): SvgNode {
  const names = classes(node);
  if (names.includes(WHERE_VIGNETTE_CLASS) && node.attrs?.["aria-hidden"] === "true") return node;
  const shown = names.includes(WHERE_VIGNETTE_CLASS) ? names : [...names, WHERE_VIGNETTE_CLASS];
  return { ...node, attrs: { ...withClasses(node.attrs ?? {}, shown), ...DECORATIVE } };
}

export function whereDrawing(node: SvgNode): SvgNode {
  if (node.tag !== "svg") return node;
  const size = viewSize(node);
  return size !== null && size.width <= WHERE_ICON_UNITS_MOST ? iconAtItsOwnSize(node, size) : asVignette(node);
}
