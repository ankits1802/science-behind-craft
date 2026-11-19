import { createElement, Fragment, type ReactNode } from "react";

import type { MonographNode } from "@/lib/monographDocument";
import { markupOf, type Attribute, type Markup, type MonographSources } from "@/lib/monographRender";

const PROP_NAMES: Readonly<Record<string, string>> = { class: "className" };

function props(attrs: readonly Attribute[]): Record<string, string> {
  return Object.fromEntries(attrs.map(([name, value]) => [PROP_NAMES[name] ?? name, value]));
}

export function markupElements(parts: readonly Markup[]): ReactNode[] {
  return parts.map((part) => (typeof part === "string" ? part : createElement(part.tag, props(part.attrs), ...markupElements(part.children))));
}

export function nodeElements(nodes: readonly MonographNode[], sources: MonographSources): ReactNode {
  return createElement(Fragment, null, ...markupElements(markupOf(nodes, sources)));
}
