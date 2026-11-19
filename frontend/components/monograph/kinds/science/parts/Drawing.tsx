import { createElement, Fragment, type ReactNode } from "react";

import type { Rich, SvgNode } from "@/lib/componentSpecsScienceParts";

import { reactProps } from "./props";

function drawn(node: SvgNode | string): ReactNode {
  if (typeof node === "string") return node;
  return createElement(node.tag, reactProps(node.attrs), ...(node.children ?? []).map(drawn));
}

export function Drawing({ node }: { node: SvgNode }) {
  return drawn(node);
}

export function Drawings({ nodes }: { nodes: SvgNode[] }) {
  return createElement(Fragment, null, ...nodes.map(drawn));
}

export function RichText({ runs }: { runs: Rich }) {
  return createElement(Fragment, null, ...runs.map((run) => (typeof run === "string" ? run : createElement(run.style, null, run.text))));
}
