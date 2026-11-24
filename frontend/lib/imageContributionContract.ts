import { apiFetch } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { boolean, integer, list, nullable, object, oneOf, optional, parseShape, text, type Shape } from "@/lib/shape";

export const IMAGE_CONTRIBUTIONS_PATH = "/contributions/images";
export const IMAGE_FILE_PATH = (id: string) => `/contributions/images/${encodeURIComponent(id)}/file`;
export const IMAGE_WITHDRAW_PATH = (id: string) => `/contributions/images/${encodeURIComponent(id)}/withdraw`;
export const IMAGE_MINE_PATH = "/contributions/images/mine";
export const IMAGE_BATCH_PATH = "/contributions/images/batch";
export const IMAGE_REVIEW_PATH = "/contributions/images/review";

export const IMAGE_ORIGINS = ["PHOTOGRAPH", "DRAWING", "AI_GENERATED"] as const;
export const SHOWN_ORIGINS = [...IMAGE_ORIGINS, "OPEN_LICENCE"] as const;
export const OPEN_SITES = ["COMMONS", "OPENVERSE", "FLICKR"] as const;
export const IMAGE_STATUSES = ["AWAITING_FILE", "PENDING", "APPROVED", "REJECTED", "WITHDRAWN"] as const;
export const IMAGE_TERMS_VERSION = "2026-11-19";
export const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp", "image/avif", "image/gif", "image/heic", "image/heif", "image/tiff", "image/bmp", "image/svg+xml"] as const;
export const IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".heic", ".heif", ".tif", ".tiff", ".bmp", ".svg"] as const;
export const IMAGE_ACCEPT = [...IMAGE_TYPES, ...IMAGE_EXTENSIONS].join(",");
export const PREVIEWED_TYPES: readonly string[] = ["image/png", "image/jpeg", "image/webp", "image/avif", "image/gif", "image/bmp", "image/svg+xml"];
export const PICTURE_SLOTS = ["MASTHEAD", "RECORD"] as const;
export const SCREEN_VERDICTS = ["CLEAR", "FLAGGED", "UNSCREENED"] as const;
export const FORMATS_HINT = "PNG, JPEG, WebP, AVIF, GIF, HEIC, TIFF, BMP or SVG, up to 10 MB. Location and camera details are removed.";
export const IMAGE_BYTES_MAX = 10 * 1024 * 1024;
export const IMAGE_TEXT_MAX = 300;
export const IMAGE_FACTS_MAX = 20;

export type ImageOrigin = (typeof IMAGE_ORIGINS)[number];
export type ShownOrigin = (typeof SHOWN_ORIGINS)[number];
export type OpenSite = (typeof OPEN_SITES)[number];
export type ImageStatus = (typeof IMAGE_STATUSES)[number];
export type PictureSlot = (typeof PICTURE_SLOTS)[number];
export type ScreenVerdict = (typeof SCREEN_VERDICTS)[number];
export type ScreenSummary = { verdict: ScreenVerdict; flags: string[]; reasons: string[] };

export const ORIGIN_LABELS: Record<ImageOrigin, string> = {
  PHOTOGRAPH: "Photograph",
  DRAWING: "Drawing",
  AI_GENERATED: "Made with AI"
};

export const SLOT_LABELS: Record<PictureSlot, string> = {
  MASTHEAD: "The first picture of the page",
  RECORD: "The GI record's picture"
};

export const IMAGE_STATUS_LABELS: Record<ImageStatus, string> = {
  AWAITING_FILE: "Waiting for its picture",
  PENDING: "Waiting for review",
  APPROVED: "Shown",
  REJECTED: "Not shown",
  WITHDRAWN: "Taken back"
};

export const IMAGE_DECLARATION =
  "I took or made this picture, or I hold the right to share it. I give the Centre of Excellence for Unified AI-Enabled Craft Ecosystem Platform, IIT Kharagpur, the right to publish it without my name. Once it is approved, this consent cannot be revoked. If an AI tool made it, I have named the tool and the prompt, and it will be shown as an illustration.";

export type ImageDeclaration = {
  craftSlug: string;
  stageId: string | null;
  claimIds: string[];
  origin: ImageOrigin;
  generator: string | null;
  prompt: string | null;
  caption: string;
  altText: string;
};

export type OpenSource = {
  site: OpenSite;
  pageUrl: string;
  fileUrl: string;
  recordUrl: string;
  title: string;
  author: string;
  licence: string;
  licenceUrl: string | null;
  credit: string;
  width: number | null;
  height: number | null;
  readAt: string;
};

export type ImageContribution = {
  id: string;
  craftSlug: string;
  craftName: string;
  stageId: string | null;
  materialId: string | null;
  slot: PictureSlot | null;
  taskKey: string | null;
  claimIds: string[];
  origin: ShownOrigin;
  label: string;
  generator: string | null;
  prompt: string | null;
  caption: string;
  altText: string;
  status: ImageStatus;
  aiMarked: boolean;
  mime: string | null;
  width: number | null;
  height: number | null;
  fileUrl: string | null;
  screen: ScreenSummary | null;
  createdAt: string;
  reviewedAt: string | null;
  reviewNote: string | null;
  openSource?: OpenSource | null;
};

export type ImageQueue = { status: ImageStatus; items: ImageContribution[] };

const screenSummaryShape: Shape<ScreenSummary> = object<ScreenSummary>({ verdict: oneOf(SCREEN_VERDICTS), flags: list(text), reasons: list(text) });

export const openSourceShape: Shape<OpenSource> = object<OpenSource>({
  site: oneOf(OPEN_SITES),
  pageUrl: text,
  fileUrl: text,
  recordUrl: text,
  title: text,
  author: text,
  licence: text,
  licenceUrl: nullable(text),
  credit: text,
  width: nullable(integer),
  height: nullable(integer),
  readAt: text
});

export const imageContributionShape: Shape<ImageContribution> = object<ImageContribution>({
  id: text,
  craftSlug: text,
  craftName: text,
  stageId: nullable(text),
  materialId: nullable(text),
  slot: nullable(oneOf(PICTURE_SLOTS)),
  taskKey: nullable(text),
  claimIds: list(text),
  origin: oneOf(SHOWN_ORIGINS),
  label: text,
  generator: nullable(text),
  prompt: nullable(text),
  caption: text,
  altText: text,
  status: oneOf(IMAGE_STATUSES),
  aiMarked: boolean,
  mime: nullable(text),
  width: nullable(integer),
  height: nullable(integer),
  fileUrl: nullable(text),
  screen: nullable(screenSummaryShape),
  createdAt: text,
  reviewedAt: nullable(text),
  reviewNote: nullable(text),
  openSource: optional(nullable(openSourceShape))
});

export const imageQueueShape: Shape<ImageQueue> = object<ImageQueue>({ status: oneOf(IMAGE_STATUSES), items: list(imageContributionShape) });

export function declarationProblems(declaration: ImageDeclaration): string[] {
  const problems: string[] = [];
  if (!declaration.craftSlug) problems.push("Choose the craft it shows.");
  if (declaration.caption.trim().length < 3) problems.push("Write a caption.");
  if (declaration.altText.trim().length < 3) problems.push("Describe the picture for readers who cannot see it.");
  if (declaration.claimIds.length > IMAGE_FACTS_MAX) problems.push(`Choose at most ${IMAGE_FACTS_MAX} facts.`);
  if (declaration.origin === "AI_GENERATED") {
    if (!declaration.generator?.trim()) problems.push("Name the AI tool and model.");
    if (!declaration.prompt?.trim()) problems.push("Give the prompt.");
    if (!declaration.claimIds.length) problems.push("Choose the facts the picture shows.");
  }
  return problems;
}

export function declarationBody(declaration: ImageDeclaration): Record<string, unknown> {
  const ai = declaration.origin === "AI_GENERATED";
  return {
    craftSlug: declaration.craftSlug,
    stageId: declaration.stageId,
    claimIds: declaration.claimIds,
    origin: declaration.origin,
    generator: ai ? declaration.generator?.trim() || null : null,
    prompt: ai ? declaration.prompt?.trim() || null : null,
    caption: declaration.caption.trim(),
    altText: declaration.altText.trim(),
    rightsConfirmed: true,
    termsVersion: IMAGE_TERMS_VERSION
  };
}

export function fileProblem(file: Pick<File, "type" | "size" | "name">): string | null {
  if (!isPictureFile(file)) return "Choose a PNG, JPEG, WebP, AVIF, GIF, HEIC, TIFF, BMP or SVG picture.";
  if (file.size > IMAGE_BYTES_MAX) return "Choose a picture of 10 MB or less.";
  return null;
}

export function isPictureFile(file: Pick<File, "type" | "name">): boolean {
  const name = file.name.toLowerCase();
  return (IMAGE_TYPES as readonly string[]).includes(file.type) || IMAGE_EXTENSIONS.some((extension) => name.endsWith(extension));
}

export function previewable(file: Pick<File, "type">): boolean {
  return PREVIEWED_TYPES.includes(file.type);
}

export function shownCredit(origin: ImageOrigin, generator: string | null): string {
  const tool = generator?.trim();
  return origin === "AI_GENERATED" ? `Illustration, made with ${tool || "the AI tool you name"}` : "Contributed to KalaVigyan";
}

export const OPEN_SITE_NAMES: Record<OpenSite, string> = { COMMONS: "Wikimedia Commons", OPENVERSE: "Openverse", FLICKR: "Flickr" };
const PHOTO_PREFIX = "Photo: ";

export function openCredit(source: Pick<OpenSource, "credit">): { prefix: string; linked: string } {
  return source.credit.startsWith(PHOTO_PREFIX) ? { prefix: PHOTO_PREFIX, linked: source.credit.slice(PHOTO_PREFIX.length) } : { prefix: "", linked: source.credit };
}

export function openReadNote(source: Pick<OpenSource, "site" | "readAt">): string {
  return `Licence and author as ${OPEN_SITE_NAMES[source.site]} records them, read ${formatDate(source.readAt)}`;
}

export function heldReasons(item: Pick<ImageContribution, "screen">): string[] {
  return item.screen && item.screen.verdict !== "CLEAR" ? item.screen.reasons : [];
}

export function sentNotice(sent: ImageContribution): string {
  if (sent.status === "APPROVED") return "Your picture is approved and shown.";
  const held = heldReasons(sent);
  return held.length ? `${IMAGE_STATUS_LABELS[sent.status]}: an Admin looks at it first. ${held.join(" ")}` : `${IMAGE_STATUS_LABELS[sent.status]}. An Admin will look at it.`;
}

export function canWithdraw(item: ImageContribution): boolean {
  return item.status === "AWAITING_FILE" || item.status === "PENDING";
}

export async function declareImage(declaration: ImageDeclaration): Promise<ImageContribution> {
  const body = await apiFetch<unknown>(IMAGE_CONTRIBUTIONS_PATH, { method: "POST", body: JSON.stringify(declarationBody(declaration)) });
  return parseShape(imageContributionShape, body);
}

export async function uploadImageFile(id: string, file: File): Promise<ImageContribution> {
  const body = await apiFetch<unknown>(IMAGE_FILE_PATH(id), { method: "PUT", body: file, headers: { "Content-Type": file.type } });
  return parseShape(imageContributionShape, body);
}

export async function fetchMyImages(): Promise<ImageContribution[]> {
  return parseShape(list(imageContributionShape), await apiFetch<unknown>(IMAGE_MINE_PATH));
}

export async function withdrawImage(id: string): Promise<ImageContribution> {
  return parseShape(imageContributionShape, await apiFetch<unknown>(IMAGE_WITHDRAW_PATH(id), { method: "POST" }));
}

export async function fetchImageQueue(status: ImageStatus): Promise<ImageQueue> {
  return parseShape(imageQueueShape, await apiFetch<unknown>(`${IMAGE_REVIEW_PATH}?state=${status}`));
}
