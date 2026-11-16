import { ApiError, apiErrorMessage } from "@/lib/api";
import type { MediaSlot } from "@/lib/craftMedia";
import { formatCalendarDay } from "@/lib/format";
import { IDEMPOTENCY_KEY_PATTERN, type MediaAsset, type MediaKind, type MediaKindOffer, type MediaShareAction } from "@/lib/mediaContract";

export const MEDIA_KIND_LABEL: Record<MediaKind, string> = { IMAGE: "Image", VIDEO: "Video" };
export const MEDIA_WAIT_LIMIT_SECONDS = 900;
export const MEDIA_POLL_MISSES = 3;
export const MEDIA_URL_MARGIN_SECONDS = 60;
export const MEDIA_LOST = "Couldn't reach the server.";
export const MEDIA_BROKEN = "Couldn't load the illustration.";
export const MEDIA_STALLED = "Still working on it.";
export const MEDIA_DOWNLOAD_FAILED = "Couldn't download. Try again.";

const RETRY_STATUSES: ReadonlySet<number> = new Set([500, 502, 504]);
const PROGRESS_STEPS = ["STARTING", "QUEUED", "RUNNING", "SUCCEEDED"] as const;
const WORKING: Record<MediaKind, string> = { IMAGE: "Drawing…", VIDEO: "Rendering…" };
const REQUESTABLE: ReadonlySet<MediaSlot["phase"]> = new Set(["ready", "ended", "refused"]);

export type MediaFailure = { retry: boolean; message: string };
export type MediaProgress = { percent: number; word: string };
export type ShareStep = { action: MediaShareAction; label: "Share" | "Stop sharing" | "Withdraw" };
export type WorkingSlot = Extract<MediaSlot, { phase: "creating" | "open" }>;

export function newIdempotencyKey(uuid: () => string): string {
  const key = `media:${uuid()}`;
  if (!IDEMPOTENCY_KEY_PATTERN.test(key)) throw new RangeError(`idempotency key ${key} is off the contract`);
  return key;
}

export function mediaFailure(error: unknown): MediaFailure {
  if (error instanceof ApiError) {
    return RETRY_STATUSES.has(error.status) ? { retry: true, message: MEDIA_LOST } : { retry: false, message: apiErrorMessage(error, MEDIA_BROKEN) };
  }
  if (error instanceof TypeError) return { retry: true, message: MEDIA_LOST };
  return { retry: false, message: MEDIA_BROKEN };
}

export function isUnexpected(error: unknown): boolean {
  return !(error instanceof ApiError) && !(error instanceof TypeError);
}

export function mayRequest(slot: MediaSlot | undefined): boolean {
  return !slot || REQUESTABLE.has(slot.phase);
}

export function slotProgress(kind: MediaKind, slot: WorkingSlot): MediaProgress {
  const step = slot.phase === "creating" ? "STARTING" : slot.job.status;
  const index = PROGRESS_STEPS.indexOf(step as (typeof PROGRESS_STEPS)[number]);
  const percent = Math.round(((Math.max(index, 0) + 1) / PROGRESS_STEPS.length) * 100);
  if (slot.phase === "creating") return { percent, word: "Starting…" };
  if (slot.job.status === "QUEUED") return { percent, word: "Queued" };
  return { percent, word: slot.job.attempts > 1 ? "Trying again…" : WORKING[kind] };
}

export function offerLabel(kind: MediaKind, hasResult: boolean): string {
  return hasResult ? `New ${MEDIA_KIND_LABEL[kind].toLowerCase()}` : MEDIA_KIND_LABEL[kind];
}

export function remainingLabel(offer: MediaKindOffer): string | null {
  return offer.remainingToday === null ? null : `${offer.remainingToday} left`;
}

export function assetCredit(asset: MediaAsset): string {
  return `${asset.label.model} · ${formatCalendarDay(asset.label.generatedOn)}`;
}

export function urlIsFresh(asset: MediaAsset, now: number): boolean {
  return Date.parse(asset.urlExpiresAt) - now > MEDIA_URL_MARGIN_SECONDS * 1000;
}

export function shareStep(asset: MediaAsset): ShareStep | null {
  const sharing = asset.sharing;
  if (!sharing) return null;
  const shared = asset.visibility === "CRAFT_SHARED";
  const action: MediaShareAction = shared || sharing.awaitingSecondProfessor ? "UNSHARE" : "SHARE";
  if (!sharing.actions.includes(action)) return null;
  return { action, label: action === "SHARE" ? "Share" : shared ? "Stop sharing" : "Withdraw" };
}

export function shareStatus(asset: MediaAsset): string | null {
  if (asset.visibility === "CRAFT_SHARED") return "Shared on the craft page";
  return asset.sharing?.awaitingSecondProfessor ? "Awaiting a second professor" : null;
}

export function slotAnnouncement(kind: MediaKind, slot: MediaSlot): string {
  const label = MEDIA_KIND_LABEL[kind];
  switch (slot.phase) {
    case "creating":
    case "open":
      return `${label}: ${slotProgress(kind, slot).word}`;
    case "ready":
      return `${label} ready.`;
    case "stalled":
      return `${label}: ${MEDIA_STALLED}`;
    default:
      return `${label}: ${slot.message}`;
  }
}
