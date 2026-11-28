import type { GateCheck, QueueAction } from "@/lib/reviewQueueContract";
import { codeLabel } from "@/lib/reviewQueueView";
import type { SectionCheck, SectionReview } from "@/lib/sectionReviewContract";

export const PROPOSED_TITLE = "Proposed";
export const NO_PUBLISHED = "The page publishes no section in this field; its facts are listed under the field.";

export function sectionHeadline(review: SectionReview): string {
  return `The ${codeLabel(review.field).toLowerCase()} section`;
}

export function publishedTitle(review: SectionReview): string {
  return review.publishedVersion === null ? "Published now" : `Published now, version ${review.publishedVersion}`;
}

export function sectionActions(review: SectionReview): QueueAction[] {
  return review.stale ? ["reject"] : ["approve", "reject"];
}

export function sectionCheckLines(checks: SectionCheck[]): GateCheck[] {
  return checks.map((check) => ({ gate: check.check, passed: check.passed, reasons: check.reasons, model: null, related: [] }));
}

export function sectionWritesLine(review: SectionReview): string {
  if (review.stale) return `The page has moved on, so it can only be rejected: ${review.stale}.`;
  return `Approving puts it in place of the ${review.subjectName} ${codeLabel(review.field).toLowerCase()} section, keeps the replaced one in the record and completes the section task; the page shows it after its next refresh.`;
}
