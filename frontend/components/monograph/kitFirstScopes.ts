import { slotDrawing } from "@/components/monograph/ComponentSlot";
import type { MonographDocument } from "@/lib/monographDocument";
import { chapterSections } from "@/lib/monographNotes";
import { chapterHeaded, componentBundles, railChapters, type ChapterBlock, type ChapterPlan, type PagePlan } from "@/lib/monographRenderLayout";
import { componentHome, type KitScope } from "@/lib/monographScopes";
import type { ShellNode } from "@/lib/monographShellTree";

const BOX_CLASS = /\bbx-(chem|pt|rm|mb|ask|sa)\b/g;
const PASSAGE_SCOPE: KitScope = "pt";
const MASTHEAD_SCOPE: KitScope = "mb";
const RAIL_SCOPE: KitScope = "chem";
const SOURCES_SCOPE: KitScope = "rm";

export function markupScopes(html: string): KitScope[] {
  return [...new Set([...html.matchAll(BOX_CLASS)].map((found) => found[1] as KitScope))];
}

function bundleScopes(document: MonographDocument, label: string): KitScope[] {
  return Object.values(componentBundles(document, label)).flatMap((bundle) => (bundle.fragment ? markupScopes(bundle.fragment) : []));
}

export function slotScopes(document: MonographDocument, label: string, scoped: boolean): KitScope[] {
  const component = document.content.components.find((found) => found.label === label);
  if (!component || slotDrawing(document, label) === "none") return [];
  const spec = Object.hasOwn(document.specs, label) ? document.specs[label] : null;
  const home = scoped ? componentHome(label, component.kind, spec).scope : null;
  return [...new Set([...(home ? [home] : []), ...bundleScopes(document, label)])];
}

function blockScopes(document: MonographDocument, block: ChapterBlock): KitScope[] {
  if (block.kind === "passage") return [PASSAGE_SCOPE];
  if (block.kind === "component") return slotScopes(document, block.label, true);
  return [SOURCES_SCOPE];
}

function openingScopes(document: MonographDocument, plan: PagePlan): KitScope[] {
  if (plan.label) return railChapters(plan).length ? [MASTHEAD_SCOPE, RAIL_SCOPE] : [MASTHEAD_SCOPE];
  return [MASTHEAD_SCOPE, ...(plan.masthead.picture ? slotScopes(document, plan.masthead.picture, false) : [])];
}

function chapterScopes(document: MonographDocument, chapter: ChapterPlan): KitScope[] {
  const subrail = !chapterHeaded(chapter) && chapterSections(document, chapter).length > 0;
  return [...(subrail ? [RAIL_SCOPE] : []), ...chapter.blocks.flatMap((block) => blockScopes(document, block))];
}

export function documentScopes(document: MonographDocument, plan: PagePlan, chapters: readonly ChapterPlan[], masthead: boolean): Set<KitScope> {
  const opening = masthead && chapters[0]?.index === 0 ? openingScopes(document, plan) : [];
  return new Set([...opening, ...chapters.flatMap((chapter) => chapterScopes(document, chapter))]);
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
