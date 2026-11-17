import type { AnswerLanguage } from "@/lib/answerLanguages";

export const DICTATION_LOCALES: Readonly<Record<string, string>> = {
  en: "en-IN",
  hi: "hi-IN",
  bn: "bn-IN",
  ta: "ta-IN",
  te: "te-IN",
  mr: "mr-IN",
  gu: "gu-IN",
  kn: "kn-IN",
  ml: "ml-IN",
  or: "or-IN",
  pa: "pa-IN",
  as: "as-IN",
  ur: "ur-IN"
};

export const LANGUAGE_REFUSED = "language-not-supported";
export const DICTATION_STOPPED = "Dictation stopped. Try again.";

const FAILURE_MESSAGES: Readonly<Record<string, string>> = {
  "no-speech": "Didn't catch that. Try again.",
  "audio-capture": "No microphone found.",
  "not-allowed": "Allow the microphone to dictate.",
  "service-not-allowed": "Allow the microphone to dictate.",
  network: "Dictation needs a connection."
};

export type HeardPiece = { transcript: string; isFinal: boolean };
export type Heard = { settled: string; pending: string };
export type DictationFailure = { message: string; refusesLanguage: boolean };

type Alternative = { readonly transcript: string };
type ResultLike = { readonly isFinal: boolean; readonly length: number; readonly [index: number]: Alternative };
export type ResultsEventLike = { readonly results: { readonly length: number; readonly [index: number]: ResultLike } };
export type ErrorEventLike = { readonly error: string };

export type Recogniser = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: ResultsEventLike) => void) | null;
  onerror: ((event: ErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
};

export type RecogniserClass = {
  new (): Recogniser;
  available?: (options: { langs: string[] }) => Promise<string>;
};

export type DictationHandlers = {
  onHeard: (heard: Heard) => void;
  onFailure: (code: string) => void;
  onEnd: () => void;
};

export type DictationSession = { stop: () => void; abort: () => void };

export function dictationLocale(code: string): string | null {
  return Object.hasOwn(DICTATION_LOCALES, code) ? DICTATION_LOCALES[code] : null;
}

export function recogniserClass(scope: object): RecogniserClass | null {
  const { SpeechRecognition, webkitSpeechRecognition } = scope as { SpeechRecognition?: unknown; webkitSpeechRecognition?: unknown };
  const found = SpeechRecognition ?? webkitSpeechRecognition;
  return typeof found === "function" ? (found as RecogniserClass) : null;
}

export function piecesOf(event: ResultsEventLike): HeardPiece[] {
  const pieces: HeardPiece[] = [];
  for (let index = 0; index < event.results.length; index++) {
    const result = event.results[index];
    if (result.length > 0) pieces.push({ transcript: result[0].transcript, isFinal: result.isFinal });
  }
  return pieces;
}

function joined(pieces: readonly HeardPiece[]): string {
  return pieces
    .map((piece) => piece.transcript.trim())
    .filter(Boolean)
    .join(" ");
}

export function heardText(pieces: readonly HeardPiece[]): Heard {
  return { settled: joined(pieces.filter((piece) => piece.isFinal)), pending: joined(pieces.filter((piece) => !piece.isFinal)) };
}

export function spokenText(heard: Heard): string {
  return [heard.settled, heard.pending].filter(Boolean).join(" ");
}

export function composeQuestion(base: string, spoken: string, limit: number): string {
  return [base.trim(), spoken.trim()].filter(Boolean).join(" ").slice(0, limit);
}

export function dictationFailure(code: string, language: AnswerLanguage): DictationFailure | null {
  if (code === "aborted") return null;
  if (code === LANGUAGE_REFUSED) return { message: `This browser can't take dictation in ${language.label}.`, refusesLanguage: true };
  return { message: FAILURE_MESSAGES[code] ?? DICTATION_STOPPED, refusesLanguage: false };
}

export async function localeOffered(Recogniser: RecogniserClass, locale: string): Promise<boolean> {
  if (typeof Recogniser.available !== "function") return true;
  try {
    return (await Recogniser.available({ langs: [locale] })) !== "unavailable";
  } catch (error) {
    console.error(error);
    return true;
  }
}

export function listeningLabel(language: AnswerLanguage): string {
  return `Listening · ${language.autonym}`;
}

export function openDictation(Recogniser: RecogniserClass, locale: string, handlers: DictationHandlers): DictationSession {
  const recogniser = new Recogniser();
  recogniser.lang = locale;
  recogniser.continuous = true;
  recogniser.interimResults = true;
  recogniser.maxAlternatives = 1;
  recogniser.onresult = (event) => handlers.onHeard(heardText(piecesOf(event)));
  recogniser.onerror = (event) => handlers.onFailure(event.error);
  recogniser.onend = () => handlers.onEnd();
  recogniser.start();
  return { stop: () => recogniser.stop(), abort: () => recogniser.abort() };
}
