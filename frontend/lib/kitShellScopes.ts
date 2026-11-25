import type { MonographDocument } from "@/lib/monographDocument";
import { componentBundles } from "@/lib/monographRenderLayout";
import type { KitScope } from "@/lib/monographScopes";
import type { ShellNode } from "@/lib/monographShellTree";

const BOX_CLASS = /\bbx-(chem|pt|rm|mb|ask|sa)\b/g;

export function markupScopes(html: string): KitScope[] {
  return [...new Set([...html.matchAll(BOX_CLASS)].map((found) => found[1] as KitScope))];
}

export function bundleScopes(document: MonographDocument, label: string): KitScope[] {
  return Object.values(componentBundles(document, label)).flatMap((bundle) => (bundle.fragment ? markupScopes(bundle.fragment) : []));
}

function nodeScopes(document: MonographDocument, node: ShellNode): KitScope[] {
  if (node.kind === "text") return [];
  if (node.kind === "slot") return bundleScopes(document, node.label);
  const own = markupScopes(node.attrs.class ?? "");
  if (node.kind === "held") return [...own, ...markupScopes(node.html)];
  return [...own, ...node.children.flatMap((child) => nodeScopes(document, child))];
}

export function shellScopes(document: MonographDocument, tree: readonly ShellNode[]): Set<KitScope> {
  return new Set(tree.flatMap((node) => nodeScopes(document, node)));
}
