import { slotDrawing } from "@/components/monograph/ComponentSlot";
import { bundleScopes } from "@/lib/kitShellScopes";
import type { MonographDocument } from "@/lib/monographDocument";
import { chapterSections } from "@/lib/monographNotes";
import { blockLabels, chapterHeaded, railChapters, type ChapterBlock, type ChapterPlan, type PagePlan } from "@/lib/monographRenderLayout";
import { componentHome, type KitScope } from "@/lib/monographScopes";

const PASSAGE_SCOPE: KitScope = "pt";
const MASTHEAD_SCOPE: KitScope = "mb";
const RAIL_SCOPE: KitScope = "chem";
const SOURCES_SCOPE: KitScope = "rm";

export function slotScopes(document: MonographDocument, label: string, scoped: boolean): KitScope[] {
  const component = document.content.components.find((found) => found.label === label);
  if (!component || slotDrawing(document, label) === "none") return [];
  const spec = Object.hasOwn(document.specs, label) ? document.specs[label] : null;
  const home = scoped ? componentHome(label, component.kind, spec).scope : null;
  return [...new Set([...(home ? [home] : []), ...bundleScopes(document, label)])];
}

function blockScopes(document: MonographDocument, block: ChapterBlock): KitScope[] {
  if (block.kind === "sources") return [SOURCES_SCOPE];
  const drawn = blockLabels(block).flatMap((label) => slotScopes(document, label, true));
  return block.kind === "passage" ? [PASSAGE_SCOPE, ...drawn] : drawn;
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
