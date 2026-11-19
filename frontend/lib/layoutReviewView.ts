import type { LayoutChange, LayoutChangeKind, LayoutEntry, LayoutReview, QueueAction } from "@/lib/reviewQueueContract";
import { codeLabel } from "@/lib/reviewQueueView";

export const CHANGES_SHOWN = 12;

export const CHANGE_LABELS: Record<LayoutChangeKind, string> = {
  ADDED: "Placed",
  CHANGED: "Moved",
  REMOVED: "Taken out"
};

export const SUBJECT_LABELS: Record<string, string> = {
  craft: "Craft page",
  family: "Family page",
  category: "Category page"
};

export function layoutActions(review: LayoutReview): QueueAction[] {
  return review.stale ? ["reject"] : ["approve", "reject"];
}

export function placeLine(entry: LayoutEntry): string {
  const parts = [`${codeLabel(entry.role)} in ${entry.chapter}, place ${entry.order}`];
  if (entry.size) parts.push(codeLabel(entry.size).toLowerCase());
  if (entry.crop) parts.push("cropped");
  if (entry.caption) parts.push(`caption “${entry.caption}”`);
  return parts.join(", ");
}

export function changeLine(change: LayoutChange): string {
  if (change.change === "ADDED" && change.after) return `${CHANGE_LABELS.ADDED}: ${placeLine(change.after)}`;
  if (change.change === "REMOVED" && change.before) return `${CHANGE_LABELS.REMOVED}: was ${placeLine(change.before)}`;
  if (change.before && change.after) return `${CHANGE_LABELS.CHANGED} from ${placeLine(change.before)} to ${placeLine(change.after)}`;
  return CHANGE_LABELS[change.change];
}

export function versionLine(review: LayoutReview): string {
  if (review.stale) {
    return `Built on version ${review.baseVersion}, but the page is at version ${review.currentVersion} now, so it can only be rejected.`;
  }
  if (review.baseVersion === 0) return "The page has no layout yet; approving writes its first version.";
  return `Built on version ${review.baseVersion}, the page's current layout; approving writes version ${review.baseVersion + 1}.`;
}

export function subjectLine(review: LayoutReview): string {
  const entries = review.entryCount === 1 ? "1 entry" : `${review.entryCount} entries`;
  return `${SUBJECT_LABELS[review.subject.kind] ?? codeLabel(review.subject.kind)} · ${entries}`;
}
