import { clip } from "./checks";
import type { Scheme } from "./matrix";
import type { AnswerRepeats, CitationCluster, OpacityAtCapture, Repeat } from "./sight";
import type { TileScan } from "./tiles";

export const FULL_OPACITY = 0.99;
export const BUSY_PATTERN = "^(?:Loading|Searching|Checking)\\b.{0,60}$";
export const MIN_PICTURE_PX = 48;
export const REGION_PANEL = '[data-testid="craft-panel-region"]';
export const REGION_MARKER = "All measurements";
export const REGION_SCREENS_MAX = 3;
export const ANSWER_SCOPE = '[data-testid="answer-view"]';

const LISTED_MAX = 6;

function percent(opacity: number): string {
  return `${Math.round(opacity * 100)}%`;
}

function listed(items: readonly string[]): string {
  return items.length > LISTED_MAX ? `${items.slice(0, LISTED_MAX).join(", ")} and ${items.length - LISTED_MAX} more` : items.join(", ");
}

export function opacityProblems(found: OpacityAtCapture): string[] {
  const problems: string[] = [];
  if (found.headline.length > 0) {
    const words = found.headline.map((faded) => `"${faded.word}" at ${percent(faded.opacity)}`);
    problems.push(`the headline is half drawn at capture: ${listed(words)}`);
  }
  if (found.largest) problems.push(`the largest element on screen is at ${percent(found.largest.opacity)} opacity at capture: ${clip(found.largest.name)}`);
  return problems;
}

export function clusterProblems(clusters: readonly CitationCluster[]): string[] {
  return clusters.map((cluster) => clip(`a citation cluster repeats a source number (${cluster.numbers.join(" ")}) after "${cluster.context}"`));
}

function repeated(repeats: readonly Repeat[]): number {
  return repeats.reduce((sum, repeat) => sum + repeat.count - 1, 0);
}

export function repeatProblems(repeats: AnswerRepeats): string[] {
  const problems: string[] = [];
  if (repeats.sentences.length > 0) {
    problems.push(clip(`the answer shows ${repeated(repeats.sentences)} repeated sentences, such as "${repeats.sentences[0].what}" ${repeats.sentences[0].count} times`, 300));
  }
  if (repeats.pictures.length > 0) {
    problems.push(clip(`the answer shows ${repeated(repeats.pictures)} repeated pictures: ${listed(repeats.pictures.map((repeat) => `${repeat.what} ${repeat.count} times`))}`, 300));
  }
  return problems;
}

export function emptyPictureProblems(pictures: readonly string[]): string[] {
  return pictures.length > 0 ? [clip(`${pictures.length} pictures show an empty frame: ${listed(pictures.map((picture) => `"${picture}"`))}`, 300)] : [];
}

export function busyProblems(texts: readonly string[]): string[] {
  return texts.length > 0 ? [clip(`${listed(texts.map((text) => `"${text}"`))} is still on screen once the page settled`)] : [];
}

export function moleculeProblems(statuses: readonly string[]): string[] {
  const failed = statuses.filter((status) => status === "failed").length;
  const pending = statuses.filter((status) => status === "waiting" || status === "loading").length;
  return [
    ...(failed > 0 ? [`${failed} 3D molecules did not load`] : []),
    ...(pending > 0 ? [`${pending} 3D molecules never reported ready`] : [])
  ];
}

export function regionProblems(runPx: number | null, screenHeight: number): string[] {
  if (runPx === null) return [];
  const screens = runPx / screenHeight;
  if (screens <= REGION_SCREENS_MAX) return [];
  return [`the Region tab runs ${screens.toFixed(1)} screens before "${REGION_MARKER}"; it must fit in ${REGION_SCREENS_MAX}`];
}

export function tileProblems(scan: TileScan): string[] {
  if (scan.flat.length === 0) return [];
  const numbers = scan.flat.map((index) => String(index + 1));
  return [`${scan.flat.length} of ${scan.judged} screen-high tiles are one flat colour: ${listed(numbers)}`];
}

export function unpaintedNotes(shotFlat: readonly number[], paintedFlat: readonly number[], screenHeight: number): string[] {
  const blank = new Set(paintedFlat);
  const unpainted = shotFlat.filter((index) => !blank.has(index));
  const [first] = unpainted;
  if (first === undefined) return [];
  return [`the full-page screenshot stops painting near ${first * screenHeight} px, so ${unpainted.length} of its tiles look blank; each was judged from its own capture`];
}

export function themeProblems(shown: string | null, expected: Scheme | null): string[] {
  if (expected === null || shown === expected) return [];
  return [`the page is drawn ${shown ?? "without a theme"}; this run asks for ${expected}`];
}
