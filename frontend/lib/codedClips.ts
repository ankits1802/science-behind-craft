import { INSTANT } from "@/lib/answerShapes";
import { API_BASE, apiFetch } from "@/lib/api";
import type { ClipLinks, FilmEnds } from "@/lib/codedFigureFrame";
import { clipFilms, type CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";
import { matching, object, parseShape, type Shape } from "@/lib/shape";

export const CLIP_LINK_PATH = (clip: string) => `/crafts/media/${encodeURIComponent(clip)}/film`;
export const CLIP_STILL_PATH = (clip: string) => `/crafts/media/${encodeURIComponent(clip)}/still`;

export function clipStillHref(clip: string): string {
  return `${API_BASE}/api${CLIP_STILL_PATH(clip)}`;
}

export type ClipLink = { url: string; expiresAt: string };
export type ClipLinkReader = (clip: string) => Promise<ClipLink>;
export type HeldClips = Readonly<Record<string, ClipLink>>;

export const clipLinkShape: Shape<ClipLink> = object<ClipLink>({ url: matching(/^https:\/\/\S+$/, "a signed address"), expiresAt: INSTANT });

export async function fetchClipLink(clip: string): Promise<ClipLink> {
  return parseShape(clipLinkShape, await apiFetch<unknown>(CLIP_LINK_PATH(clip)));
}

export async function clipLinks(figure: Pick<CodedFigureSpec, "films">, read: ClipLinkReader = fetchClipLink): Promise<HeldClips> {
  const films = clipFilms(figure);
  const settled = await Promise.allSettled(films.map((film) => read(film.clip)));
  const found: Record<string, ClipLink> = {};
  films.forEach((film, at) => {
    const link = settled[at];
    if (link?.status === "fulfilled") found[film.key] = link.value;
  });
  return found;
}

export function linkEnd(link: ClipLink): number {
  return Date.parse(link.expiresAt);
}

export function clipAddresses(held: HeldClips): ClipLinks {
  return Object.fromEntries(Object.entries(held).map(([key, link]) => [key, link.url]));
}

export function clipEnds(held: HeldClips): FilmEnds {
  return Object.fromEntries(Object.entries(held).map(([key, link]) => [key, linkEnd(link)]));
}
