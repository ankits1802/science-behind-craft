import { DISCIPLINES, type Discipline } from "@/lib/explainerBlockBase";
import { DISCIPLINE_LABEL } from "@/lib/explainerView";
import { byCount } from "@/lib/format";
import type { FacetNews, Notification } from "@/lib/learningContract";

export const ASK_PATH = "/ask";
export const SAVED_PATH = "/saved";
export const EXPLAINER_PARAM = "explainer";
export const VERSION_PARAM = "version";
export const UPDATE_PARAM = "update";
export const NOTE_TITLE = "This answer got better";
export const NOTES_SHOWN_MAX = 50;

const FACET_SEPARATOR = ",";

export function explainerHref(explainerId: string, version: number | null = null): string {
  const search = new URLSearchParams([[EXPLAINER_PARAM, explainerId]]);
  if (version !== null) search.set(VERSION_PARAM, String(version));
  return `${ASK_PATH}?${search.toString()}`;
}

export function updateHref(note: Notification): string {
  const search = new URLSearchParams([
    [EXPLAINER_PARAM, note.payload.explainerId],
    [UPDATE_PARAM, note.payload.news.map((item) => item.facet).join(FACET_SEPARATOR)]
  ]);
  return `${ASK_PATH}?${search.toString()}`;
}

export function updateFacets(param: string | null): Discipline[] {
  if (!param) return [];
  const known = new Set<string>(DISCIPLINES);
  return [...new Set(param.split(FACET_SEPARATOR).map((part) => part.trim()))].filter((part): part is Discipline => known.has(part));
}

export function newsText(news: readonly FacetNews[]): string {
  return news
    .map((item, index) => {
      const label = DISCIPLINE_LABEL[item.facet];
      if (index > 0) return `${item.newClaims} in ${label}`;
      return `${item.newClaims} new ${byCount(item.newClaims, "finding", "findings")} in ${label}`;
    })
    .join(" · ");
}

export function unreadText(unread: number): string | null {
  if (unread <= 0) return null;
  return `${unread} new ${byCount(unread, "note", "notes")}`;
}

export type DigestChoice = { offered: boolean; on: boolean };

export function digestChoice(raw: unknown): DigestChoice {
  if (!raw || typeof raw !== "object") return { offered: false, on: false };
  const body = raw as { alertDigest?: unknown; alertDigestOffered?: unknown };
  return { offered: body.alertDigestOffered === true, on: body.alertDigest === true };
}

export function notesCapText(shown: number): string | null {
  return shown >= NOTES_SHOWN_MAX ? `Showing the latest ${NOTES_SHOWN_MAX}.` : null;
}
