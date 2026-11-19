import type { ItemOrigin } from "@/lib/craftChapters";

export const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;
export const DAY = /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;
export const ORIGIN_LABELS = {
  STORED: "From earlier research",
  READERS: "From a reader's question",
  MODEL: "Model-built from cited claims",
  AI_IMAGE: "AI illustration",
  AI_VIDEO: "AI video"
} as const;

export type OriginLines = { basis: string | null; question: string | null; generated: string | null; madeBy: string | null };

const MONTH_LABEL = new Intl.DateTimeFormat("en-IN", { month: "long", year: "numeric", timeZone: "UTC" });
const DAY_LABEL = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });

export function askedMonth(month: string): string {
  if (!MONTH.test(month)) throw new RangeError(`not a month: ${month}`);
  const [year, number] = month.split("-").map(Number);
  return MONTH_LABEL.format(new Date(Date.UTC(year, number - 1, 1)));
}

function madeOn(day: string): string {
  if (!DAY.test(day)) throw new RangeError(`not a day: ${day}`);
  const [year, month, date] = day.split("-").map(Number);
  return DAY_LABEL.format(new Date(Date.UTC(year, month - 1, date)));
}

export function originLabel(origin: ItemOrigin | null): OriginLines {
  if (origin === null) return { basis: null, question: null, generated: null, madeBy: null };
  const asked = origin.fromQuestion?.text ?? null;
  const basis =
    origin.basis === "CURATED" ? null : origin.basis === "STORED" ? ORIGIN_LABELS.STORED : asked && origin.fromQuestion ? `${ORIGIN_LABELS.READERS}, ${askedMonth(origin.fromQuestion.askedIn)}` : ORIGIN_LABELS.READERS;
  const generated = origin.generated ? ORIGIN_LABELS[origin.generated] : null;
  const madeBy = origin.model && origin.generatedOn ? `${origin.model}, ${madeOn(origin.generatedOn)}` : null;
  return { basis, question: asked, generated, madeBy };
}
