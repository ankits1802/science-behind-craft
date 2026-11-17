import { apiFetch, buildQuery } from "@/lib/api";
import { languageCodeShape } from "@/lib/answerLanguages";
import { HTTPS_URL, UUID } from "@/lib/answerShapes";
import type { TextRange } from "@/lib/explainerView";
import { list, number, object, oneOf, parseShape, ShapeError, text, type Shape } from "@/lib/shape";

export type ListenWord = { sentenceId: string; text: string; start: number; end: number };
export type ListenTrack = { blockId: string; audioUrl: string; durationSeconds: number; words: ListenWord[] };
export type ListenScript = { schemaVersion: 1; answerId: string; language: string; tracks: ListenTrack[] };
export type ListenPosition = { track: number; time: number };
export type ListenMark = { sentenceId: string; words: ListenWord[]; wordIndex: number };

export const LISTEN_RATES = [1, 1.25, 1.5] as const;

const listenWordShape: Shape<ListenWord> = object<ListenWord>({ sentenceId: text, text, start: number, end: number });

const listenScriptShape: Shape<ListenScript> = object<ListenScript>({
  schemaVersion: oneOf([1] as const),
  answerId: UUID,
  language: languageCodeShape,
  tracks: list(object<ListenTrack>({ blockId: text, audioUrl: HTTPS_URL, durationSeconds: number, words: list(listenWordShape, 1) }), 1)
});

const listenOfferShape = object<{ languages: string[] }>({ languages: list(languageCodeShape) });

export function listenPath(answerId: string, language: string): string {
  return `/answers/${encodeURIComponent(answerId)}/listen${buildQuery({ language })}`;
}

function checkTrack(track: ListenTrack, index: number): void {
  const path = `listen.tracks[${index}]`;
  if (!(track.durationSeconds > 0)) throw new ShapeError(`${path}.durationSeconds`, "a positive length");
  let previous = 0;
  track.words.forEach((word, at) => {
    if (word.text === "" || word.start < previous || word.end < word.start || word.start > track.durationSeconds) {
      throw new ShapeError(`${path}.words[${at}]`, "a word timed in reading order within the track");
    }
    previous = word.start;
  });
}

export function checkedScript(raw: unknown, answerId: string, language: string): ListenScript {
  const script = parseShape(listenScriptShape, raw);
  if (script.answerId !== answerId) throw new ShapeError("listen.answerId", `the answer ${answerId}`);
  if (script.language !== language) throw new ShapeError("listen.language", `the language ${language}`);
  script.tracks.forEach(checkTrack);
  return script;
}

export async function fetchListenScript(answerId: string, language: string): Promise<ListenScript> {
  return checkedScript(await apiFetch<unknown>(listenPath(answerId, language)), answerId, language);
}

export function listenLanguagesOf(raw: unknown): string[] {
  if (raw === undefined || raw === null) return [];
  try {
    return parseShape(listenOfferShape, raw).languages;
  } catch (error) {
    if (!(error instanceof ShapeError)) throw error;
    console.error(new ShapeError(`answers/config listen.${error.path}`, error.expected));
    return [];
  }
}

export function scriptDuration(script: ListenScript): number {
  return script.tracks.reduce((sum, track) => sum + track.durationSeconds, 0);
}

export function elapsedOf(script: ListenScript, position: ListenPosition): number {
  const before = script.tracks.slice(0, position.track).reduce((sum, track) => sum + track.durationSeconds, 0);
  return before + Math.max(0, position.time);
}

export function activeWordIndex(words: readonly ListenWord[], time: number): number {
  let low = 0;
  let high = words.length - 1;
  let found = -1;
  while (low <= high) {
    const middle = (low + high) >> 1;
    if (words[middle].start <= time) {
      found = middle;
      low = middle + 1;
    } else high = middle - 1;
  }
  return found;
}

export function listenMark(script: ListenScript | null, position: ListenPosition): ListenMark | null {
  return trackMark(script?.tracks[position.track]?.words ?? [], position.time);
}

export function trackMark(words: readonly ListenWord[], time: number): ListenMark | null {
  const index = activeWordIndex(words, time);
  if (index < 0) return null;
  const sentenceId = words[index].sentenceId;
  const ofSentence = words.filter((word) => word.sentenceId === sentenceId);
  return { sentenceId, words: ofSentence, wordIndex: ofSentence.indexOf(words[index]) };
}

export function wordRanges(shown: string, words: readonly { text: string }[]): (TextRange | null)[] {
  let from = 0;
  return words.map((word) => {
    const at = shown.indexOf(word.text, from);
    if (at < 0) return null;
    from = at + word.text.length;
    return { from: at, to: from };
  });
}

export function nextRate(rate: number): number {
  const index = LISTEN_RATES.findIndex((option) => option === rate);
  return LISTEN_RATES[(index + 1) % LISTEN_RATES.length];
}
