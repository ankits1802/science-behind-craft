import { formatDateTime } from "@/lib/format";
import type { CheckState, PictureVerdict, VerdictView } from "@/lib/pictureCheckContract";
import type { QueueAction } from "@/lib/reviewQueueContract";

export const PICTURE_CHECK_ACTIONS: QueueAction[] = ["approve", "reject"];
export const PICTURE_CHECK_OUTCOME =
  "Approve shows the picture beside this fact as seen by a person. Reject takes it off this fact; the picture and its other facts stay.";

export const VERDICT_LABELS: Record<PictureVerdict, string> = {
  SHOWS: "Shows what the fact says",
  DOES_NOT_SHOW: "Does not show it"
};

export const CHECK_STATE_LABELS: Record<CheckState, string> = {
  SEEN: "Shown as seen",
  WAITING: "Shown by its title, waiting for a second look",
  HIDDEN: "Hidden from this fact",
  IN_REVIEW: "Hidden from this fact until an Admin decides"
};

export function verdictByLine(verdict: VerdictView): string {
  const who = verdict.by ?? "A removed account";
  const role = verdict.ruling ? "an Admin's decision" : verdict.trusted ? "an account that publishes at once" : "an account whose work is reviewed";
  return `${who}, ${role}, ${formatDateTime(verdict.at)}`;
}
