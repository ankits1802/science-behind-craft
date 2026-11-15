import anyAscii from "any-ascii";

export const PORTAL = "KalaVigyan";
export const TITLE_MAX = 120;
export const FILE_MAX = 150;
export const SUBJECT_MIN = 40;
export const MAX_TITLE = TITLE_MAX;
export const MAX_FILE_NAME = FILE_MAX;
export const MIN_SUBJECT = SUBJECT_MIN;

const IST_OFFSET_MS = 330 * 60 * 1000;
const RESERVED_STEMS: ReadonlySet<string> = new Set([
  "CON",
  "PRN",
  "AUX",
  "NUL",
  ...Array.from({ length: 9 }, (_, i) => `COM${i + 1}`),
  ...Array.from({ length: 9 }, (_, i) => `LPT${i + 1}`)
]);
const ZW = new Set(["‌", "‍"]);
const VERSION = /^v\d+(?:\.\d+)*$/;
const INDIC_BLOCKS = [0x0900, 0x0980, 0x0a00, 0x0a80, 0x0b00, 0x0b80, 0x0c00, 0x0c80, 0x0d00];
const WORD_CHAR = /[\p{L}\p{M}\p{Nd}]/u;
const DIGIT = /\p{Nd}/u;

const cpLength = (value: string) => [...value].length;

function indic(cp: number): [number, number] | null {
  for (const base of INDIC_BLOCKS) if (cp >= base && cp < base + 0x80) return [base, cp - base];
  return null;
}
const isConsonant = (off: number) => (off >= 0x15 && off <= 0x39) || (off >= 0x58 && off <= 0x5f);
const isVowelSignOrVirama = (off: number) => (off >= 0x3e && off <= 0x4d) || (off >= 0x55 && off <= 0x57) || off === 0x62 || off === 0x63;
const isWordLetter = (off: number) => isConsonant(off) || (off >= 0x05 && off <= 0x14) || (off >= 0x01 && off <= 0x03) || off === 0x60 || off === 0x61;

export function indicInherentVowels(value: string): string {
  const chars = [...value].filter((ch) => indic(ch.codePointAt(0)!)?.[1] !== 0x3c);
  const out: string[] = [];
  chars.forEach((ch, i) => {
    out.push(ch);
    const info = indic(ch.codePointAt(0)!);
    if (info && isConsonant(info[1]) && i + 1 < chars.length) {
      const next = indic(chars[i + 1].codePointAt(0)!);
      if (next && next[0] === info[0] && !isVowelSignOrVirama(next[1]) && isWordLetter(next[1])) out.push("a");
    }
  });
  return out.join("");
}

export function toAscii(value: string | null | undefined): string {
  if (!value) return "";
  return anyAscii(indicInherentVowels(String(value).normalize("NFC")));
}

export const transliterate = toAscii;

const text = (value: unknown): string => (value === null || value === undefined ? "" : String(value));

export function splitWords(value: unknown): string[] {
  const words: string[] = [];
  let current = "";
  for (const ch of text(value).normalize("NFC")) {
    if (ZW.has(ch) || WORD_CHAR.test(ch)) current += ch;
    else if (current) {
      words.push(current);
      current = "";
    }
  }
  if (current) words.push(current);
  return words;
}

export function titleCaseWord(word: string): string {
  if ([...word].some((ch) => DIGIT.test(ch))) return word;
  const n = cpLength(word);
  if (n >= 2 && n <= 3 && /^[A-Z]+$/.test(word)) return word;
  const [first, ...rest] = [...word];
  if (first && first.toUpperCase() !== first.toLowerCase()) return first.toUpperCase() + rest.join("").toLowerCase();
  return word;
}

export function fieldWords(value: unknown, asciiOnly: boolean): string[] {
  const raw = text(value);
  let words = splitWords(asciiOnly ? toAscii(raw) : raw);
  if (asciiOnly) words = words.map((w) => w.replace(/[^A-Za-z0-9]/g, "")).filter(Boolean);
  return words.map(titleCaseWord);
}

const joinField = (words: string[]) => words.join("-");
const fields = (...parts: (string | null | undefined)[]) => parts.filter(Boolean).join("_");

export function field(value: unknown, asciiOnly = true): string {
  return joinField(fieldWords(value, asciiOnly));
}

function same(a: unknown, b: unknown): boolean {
  if (splitWords(a).join(" ").toLowerCase() === splitWords(b).join(" ").toLowerCase()) return true;
  const fa = field(a).toLowerCase();
  return fa !== "" && fa === field(b).toLowerCase();
}

export function placeText(locality: unknown, district: unknown, state: unknown): string | null {
  const loc = text(locality).trim();
  const dist = text(district).trim();
  const st = text(state).trim();
  if (loc && dist && !same(loc, dist)) return `${loc} ${dist}`;
  return loc || dist || st || null;
}

type Render = (place: string[], craft: string[], subject: string[]) => string;

function fit(render: Render, place: string[], craft: string[], subject: string[], limit: number): string {
  const tooLong = () => cpLength(render(place, craft, subject)) > limit;
  while (tooLong() && subject.length > 1 && cpLength(joinField(subject)) > SUBJECT_MIN) subject.pop();
  while (tooLong() && craft.length > 1) craft.pop();
  while (tooLong() && place.length > 1) place.pop();
  while (tooLong() && subject.length > 1) subject.pop();
  if (tooLong() && craft.length) craft.length = 0;
  if (tooLong() && place.length) place.length = 0;
  while (tooLong() && subject.length && cpLength(subject[0]) > 1) subject[0] = [...subject[0]].slice(0, -1).join("");
  if (tooLong()) subject.length = 0;
  return render(place, craft, subject);
}

export type When = Date | string | null | undefined;

type IstMoment = { date: string; time: string | null };

export function asIst(value: When): IstMoment | null {
  if (value === null || value === undefined || value === "") return null;
  let ms: number;
  if (typeof value === "string") {
    const t = value.trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return { date: t, time: null };
    const zoned = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(t) ? t : `${t}Z`;
    ms = Date.parse(zoned);
  } else {
    ms = value.getTime();
  }
  if (Number.isNaN(ms)) return null;
  const iso = new Date(ms + IST_OFFSET_MS).toISOString();
  return { date: iso.slice(0, 10), time: iso.slice(11, 13) + iso.slice(14, 16) };
}

function istDay(value: When): string | null {
  return asIst(value)?.date ?? null;
}

export function istParts(iso: string): { date: string; time: string } | null {
  const m = asIst(iso);
  return m && m.time ? { date: m.date, time: m.time } : null;
}

export function istToday(now: Date = new Date()): string {
  return asIst(now)!.date;
}

const guard = (stem: string) => (RESERVED_STEMS.has(stem.toUpperCase()) ? `${stem}-File` : stem);

function extension(ext: unknown): string {
  return text(ext)
    .trim()
    .replace(/^\.+/, "")
    .replace(/[^A-Za-z0-9.]/g, "")
    .toLowerCase()
    .replace(/\.{2,}/g, ".")
    .replace(/^\.+|\.+$/g, "");
}

function sequenceField(value: unknown): string | null {
  const t = text(value).trim();
  if (!t) return null;
  if (VERSION.test(t)) return t;
  return joinField(fieldWords(t, true)) || null;
}

export type FileNameInput = {
  entity?: unknown;
  what?: unknown;
  ext?: unknown;
  day?: When;
  time?: string | boolean | null;
  place?: unknown;
  craft?: unknown;
  subject?: unknown;
  sequence?: unknown;
  n?: number | null;
  portal?: string | null;
  date?: When;
  period?: unknown;
};

export function fileName(input: FileNameInput): string {
  const moment = input.period ? null : asIst(input.date !== undefined && input.date !== null ? input.date : input.day);
  const day = input.period ? joinField(fieldWords(input.period, true)) : (moment?.date ?? null);
  let time: string | null = null;
  if (typeof input.time === "string") time = input.time || null;
  else if (input.time && !input.period) time = moment?.time ?? null;
  const ext = extension(input.ext);
  const portal = (input.portal || PORTAL).replace(/[^A-Za-z0-9-]/g, "");
  const entity = joinField(fieldWords(input.entity, true));
  const what = joinField(fieldWords(input.what, true));
  const sequence = sequenceField(input.sequence);
  const n = input.n && input.n > 1 ? String(Math.trunc(input.n)) : null;
  return fit(
    (p, c, s) => {
      const stem = guard(fields(portal, entity, day, time, joinField(p), joinField(c), joinField(s), what, sequence, n));
      return ext ? `${stem}.${ext}` : stem;
    },
    fieldWords(input.place, true),
    fieldWords(input.craft, true),
    fieldWords(input.subject, true),
    FILE_MAX
  );
}

export type ExportInput = Omit<FileNameInput, "date" | "time" | "entity" | "what" | "ext"> & {
  at?: When;
  time?: string | null;
  withTime?: boolean;
  dated?: boolean;
};

export type ExportNameInput = ExportInput & { entity: string; what: string; ext: string };

export function exportFilename(input: ExportNameInput): string;
export function exportFilename(entity: unknown, what: unknown, ext: string, opts?: ExportInput): string;
export function exportFilename(first: unknown, what?: unknown, ext?: string, opts: ExportInput = {}): string {
  let entity = first;
  let options = opts;
  if (first && typeof first === "object" && "what" in (first as object) && what === undefined) {
    const { entity: e, what: w, ext: x, ...rest } = first as ExportNameInput;
    entity = e;
    what = w;
    ext = x;
    options = rest;
  }
  const { at, day, time, withTime = false, dated = true, ...rest } = options;
  let when: When = null;
  if (!rest.period && dated) when = day != null && day !== "" ? (typeof day === "string" ? day.trim().slice(0, 10) : istDay(day)) : (at ?? new Date());
  return fileName({ ...rest, entity, what, ext, date: when, time: time || withTime });
}
