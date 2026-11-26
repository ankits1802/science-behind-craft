import { INSTANT } from "@/lib/answerShapes";
import { apiFetch } from "@/lib/api";
import type { ClipLinks } from "@/lib/codedFigureFrame";
import { clipFilms, type CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";
import { matching, object, parseShape, type Shape } from "@/lib/shape";

export const CLIP_LINK_PATH = (clip: string) => `/crafts/media/${encodeURIComponent(clip)}/film`;

export type ClipLink = { url: string; expiresAt: string };
export type ClipLinkReader = (clip: string) => Promise<ClipLink>;

export const clipLinkShape: Shape<ClipLink> = object<ClipLink>({ url: matching(/^https:\/\/\S+$/, "a signed address"), expiresAt: INSTANT });

export async function fetchClipLink(clip: string): Promise<ClipLink> {
  return parseShape(clipLinkShape, await apiFetch<unknown>(CLIP_LINK_PATH(clip)));
}

export async function clipLinks(figure: Pick<CodedFigureSpec, "films">, read: ClipLinkReader = fetchClipLink): Promise<ClipLinks> {
  const films = clipFilms(figure);
  const settled = await Promise.allSettled(films.map((film) => read(film.clip)));
  const found: Record<string, string> = {};
  films.forEach((film, at) => {
    const link = settled[at];
    if (link?.status === "fulfilled") found[film.key] = link.value.url;
  });
  return found;
}
