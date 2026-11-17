import type { Explainer } from "@/lib/explainerContract";
import type { ExplainerRef } from "@/lib/explainerState";
import { byCount } from "@/lib/format";
import type { CitationFormat, LessonFormat, LessonRequest, Slide } from "@/lib/lessonContract";

export const LESSON_SECTIONS_MAX = 14;
export const LESSONS_HOME = "/lessons";
export const NEW_LESSON_PATH = "/lessons/new";

export const LESSON_FORMAT_LABEL: Record<LessonFormat, string> = { pptx: "Slides · PPTX", pdf: "Handout · PDF", html: "Web slides · HTML" };
export const LESSON_FORMAT_ORDER: readonly LessonFormat[] = ["pptx", "pdf", "html"];
export const CITATION_FORMAT_LABEL: Record<CitationFormat, string> = { txt: "APA", bib: "BibTeX", ris: "RIS", json: "CSL-JSON" };
export const CITATION_FORMAT_ORDER: readonly CitationFormat[] = ["txt", "bib", "ris", "json"];

export type LessonSection = { id: string; title: string; blocks: number };

export function lessonSections(explainer: Explainer): LessonSection[] {
  return [...explainer.sections]
    .filter((section) => section.state === "READY" && section.blocks.length > 0)
    .sort((a, b) => a.order - b.order)
    .map((section) => ({ id: section.id, title: section.title, blocks: section.blocks.length }));
}

export function newLessonHref(ref: ExplainerRef): string {
  const search = new URLSearchParams([
    ["explainer", ref.explainerId],
    ["version", String(ref.version)]
  ]);
  return `${NEW_LESSON_PATH}?${search.toString()}`;
}

export function lessonHref(lessonId: string): string {
  return `${LESSONS_HOME}/${encodeURIComponent(lessonId)}`;
}

export function chosenInOrder(sections: readonly LessonSection[], chosen: ReadonlySet<string>): string[] {
  return sections.filter((section) => chosen.has(section.id)).map((section) => section.id);
}

export function lessonRequest(ref: ExplainerRef, title: string, sectionIds: readonly string[], quiz: boolean): LessonRequest | null {
  if (sectionIds.length === 0 || sectionIds.length > LESSON_SECTIONS_MAX || new Set(sectionIds).size !== sectionIds.length) return null;
  const named = title.trim();
  return { explainerId: ref.explainerId, version: ref.version, title: named || null, sectionIds: [...sectionIds], quiz };
}

export function slideCaption(slide: Slide, total: number): string {
  return `Slide ${slide.number} of ${total}`;
}

export function slideCountText(count: number): string {
  return `${count} ${byCount(count, "slide", "slides")}`;
}
