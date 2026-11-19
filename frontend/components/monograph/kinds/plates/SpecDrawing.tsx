import { createElement, type ReactNode } from "react";

import type { DrawingElement } from "@/lib/componentSpecsPlates";

const KEPT_PREFIXES = ["data-", "aria-"];
const RENAMED: Readonly<Record<string, string>> = { class: "className", "xlink:href": "xlinkHref", "xml:space": "xmlSpace" };

function propName(name: string): string {
  if (RENAMED[name]) return RENAMED[name];
  if (KEPT_PREFIXES.some((prefix) => name.startsWith(prefix))) return name;
  return name.replace(/-([a-z])/g, (_, letter: string) => letter.toUpperCase());
}

export function styleObject(style: string): Record<string, string> {
  const entries = style
    .split(";")
    .map((rule) => rule.split(":"))
    .filter((parts) => parts.length >= 2 && parts[0].trim())
    .map(([name, ...value]) => {
      const property = name.trim();
      const key = property.startsWith("--") ? property : property.replace(/-([a-z])/g, (_, letter: string) => letter.toUpperCase());
      return [key, value.join(":").trim()] as const;
    });
  return Object.fromEntries(entries);
}

function drawingProps(attrs: Record<string, string>, key: number): Record<string, unknown> {
  const props: Record<string, unknown> = { key };
  for (const [name, value] of Object.entries(attrs)) props[propName(name)] = name === "style" ? styleObject(value) : value;
  return props;
}

export function drawingNode(node: DrawingElement | string, key: number): ReactNode {
  if (typeof node === "string") return node;
  return createElement(node.tag, drawingProps(node.attrs, key), ...node.children.map((child, index) => drawingNode(child, index)));
}

export function SpecDrawing({ element }: { element: DrawingElement }) {
  return drawingNode(element, 0);
}

export function SpecDrawings({ elements }: { elements: DrawingElement[] }) {
  return <>{elements.map((element, index) => drawingNode(element, index))}</>;
}
