import { apiFetch, buildQuery } from "@/lib/api";
import { languageCodeShape } from "@/lib/answerLanguages";
import { HTTPS_URL, INSTANT, UUID } from "@/lib/answerShapes";
import { BLOCK_ID } from "@/lib/explainerBlockBase";
import { boolean, list, matching, nullable, number, object, oneOf, parseShape, ShapeError, text, type Shape } from "@/lib/shape";

export const SCORE_LABEL = "AI music and sound";

export type ScoreMusic = { audioUrl: string; durationSeconds: number; model: string };
export type ScoreCue = { blockId: string; offsetSeconds: number; audioUrl: string; durationSeconds: number; model: string };
export type ScoreLabel = { text: typeof SCORE_LABEL; models: string[]; generatedOn: string };
export type FilmScore = {
  schemaVersion: 1;
  answerId: string;
  language: string;
  music: ScoreMusic | null;
  cues: ScoreCue[];
  label: ScoreLabel;
  urlExpiresAt: string;
};
export type FilmOffer = { score: boolean };

const filmScoreShape: Shape<FilmScore> = object<FilmScore>({
  schemaVersion: oneOf([1] as const),
  answerId: UUID,
  language: languageCodeShape,
  music: nullable(object<ScoreMusic>({ audioUrl: HTTPS_URL, durationSeconds: number, model: text })),
  cues: list(object<ScoreCue>({ blockId: BLOCK_ID, offsetSeconds: number, audioUrl: HTTPS_URL, durationSeconds: number, model: text })),
  label: object<ScoreLabel>({
    text: oneOf([SCORE_LABEL] as const),
    models: list(text, 1),
    generatedOn: matching(/^\d{4}-\d{2}-\d{2}$/, "a calendar day")
  }),
  urlExpiresAt: INSTANT
});

export const filmOfferShape: Shape<FilmOffer> = object<FilmOffer>({ score: boolean });

export function filmScoreOffered(raw: unknown): boolean {
  if (raw === undefined || raw === null) return false;
  try {
    return parseShape(filmOfferShape, raw).score;
  } catch (error) {
    if (!(error instanceof ShapeError)) throw error;
    console.error(new ShapeError(`answers/config film.${error.path}`, error.expected));
    return false;
  }
}

export async function fetchFilmScore(answerId: string, language: string): Promise<FilmScore> {
  return checkedFilmScore(await apiFetch<unknown>(filmScorePath(answerId, language)), answerId, language);
}

export function filmScorePath(answerId: string, language: string): string {
  return `/answers/${encodeURIComponent(answerId)}/film-score${buildQuery({ language })}`;
}

export function checkedFilmScore(raw: unknown, answerId: string, language: string): FilmScore {
  const score = parseShape(filmScoreShape, raw);
  if (score.answerId !== answerId) throw new ShapeError("score.answerId", `the answer ${answerId}`);
  if (score.language !== language) throw new ShapeError("score.language", `the language ${language}`);
  if (score.music === null && score.cues.length === 0) throw new ShapeError("score", "music or a cue");
  const scenes = score.cues.map((cue) => cue.blockId);
  if (new Set(scenes).size !== scenes.length) throw new ShapeError("score.cues", "one cue per scene at most");
  if (score.cues.some((cue) => cue.offsetSeconds < 0 || !(cue.durationSeconds > 0))) {
    throw new ShapeError("score.cues", "cues placed at or after their scene's start");
  }
  return score;
}
