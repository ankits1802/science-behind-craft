import { formatCalendarDay } from "@/lib/format";

const MILLISECONDS_PER_SECOND = 1000;
const SECONDS_PER_MINUTE = 60;

export function playerClock(milliseconds: number): string {
  const seconds = Math.round(milliseconds / MILLISECONDS_PER_SECOND);
  return `${Math.floor(seconds / SECONDS_PER_MINUTE)}:${String(seconds % SECONDS_PER_MINUTE).padStart(2, "0")}`;
}

export function playerTime(restMs: number, durationMs: number): string {
  return `${playerClock(restMs)} / ${playerClock(durationMs)}`;
}

export function drawnFrom(sentences: readonly number[]): string {
  return sentences.length === 1 ? `sentence ${sentences[0]}` : `sentences ${sentences.join(", ")}`;
}

export function illustrationCaption(subject: string, sentences: readonly number[]): string {
  return `${subject}. Drawn from ${drawnFrom(sentences)} of this section; not a photograph.`;
}

export function illustrationMeta(made: string): string {
  return `AI illustration · ${formatCalendarDay(made)}`;
}

export function videoMeta(durationMs: number, made: string): string {
  return `AI video · ${Math.round(durationMs / MILLISECONDS_PER_SECOND)} seconds, silent · ${formatCalendarDay(made)}`;
}

export function sceneName(number: number, title: string, forming: boolean): string {
  return `Scene ${number}: ${title}${forming ? ", arriving" : ""}`;
}

export function panelCount(number: number, total: number): string {
  return `Panel ${number} of ${total}. `;
}
