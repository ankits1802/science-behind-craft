import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { ENGLISH, resolvedLanguage, type AnswerLanguage } from "@/lib/answerLanguages";
import {
  composeQuestion,
  DICTATION_LOCALES,
  DICTATION_STOPPED,
  dictationFailure,
  dictationLocale,
  heardText,
  listeningLabel,
  localeOffered,
  openDictation,
  recogniserClass,
  spokenText,
  type ErrorEventLike,
  type Recogniser,
  type RecogniserClass,
  type ResultsEventLike
} from "@/lib/dictation";

import { gapCopyFindings } from "./production/checks";

const VOCABULARY = join(__dirname, "..", "..", "backend", "app", "research", "vocabulary.py");

const HINDI: AnswerLanguage = { code: "hi", label: "Hindi", autonym: "हिन्दी", script: "Deva", direction: "ltr" };
const TAMIL: AnswerLanguage = { code: "ta", label: "Tamil", autonym: "தமிழ்", script: "Taml", direction: "ltr" };
const ODIA: AnswerLanguage = { code: "or", label: "Odia", autonym: "ଓଡ଼ିଆ", script: "Orya", direction: "ltr" };
const OFFERED = [ENGLISH, HINDI, TAMIL, ODIA];

function backendLanguageCodes(): string[] {
  const text = readFileSync(VOCABULARY, "utf8");
  return [...text.matchAll(/^\s+"([a-z]{2,3})": AnswerLanguageSpec\(/gm)].map((found) => found[1]);
}

function quietly<T>(run: () => Promise<T>): Promise<{ value: T; logged: unknown[] }> {
  const logged: unknown[] = [];
  const original = console.error;
  console.error = (...args: unknown[]) => void logged.push(...args);
  return run()
    .then((value) => ({ value, logged }))
    .finally(() => {
      console.error = original;
    });
}

type FakeResult = { isFinal: boolean; length: number; [index: number]: { transcript: string } };

function result(transcript: string, isFinal: boolean): FakeResult {
  return { isFinal, length: 1, 0: { transcript } };
}

function resultsEvent(...results: FakeResult[]): ResultsEventLike {
  return { results: Object.assign({}, results, { length: results.length }) };
}

class FakeRecogniser implements Recogniser {
  static made: FakeRecogniser[] = [];
  lang = "";
  continuous = false;
  interimResults = false;
  maxAlternatives = 0;
  onresult: ((event: ResultsEventLike) => void) | null = null;
  onerror: ((event: ErrorEventLike) => void) | null = null;
  onend: (() => void) | null = null;
  calls: string[] = [];
  constructor() {
    FakeRecogniser.made.push(this);
  }
  start() {
    this.calls.push("start");
  }
  stop() {
    this.calls.push("stop");
  }
  abort() {
    this.calls.push("abort");
  }
}

test("every answer language has a recogniser locale: the language with India as its region", () => {
  expect(Object.keys(DICTATION_LOCALES)).toEqual(backendLanguageCodes());
  expect(backendLanguageCodes()).toHaveLength(13);
  expect(dictationLocale("en")).toBe("en-IN");
  expect(dictationLocale("hi")).toBe("hi-IN");
  expect(dictationLocale("ta")).toBe("ta-IN");
  expect(dictationLocale("or")).toBe("or-IN");
  expect(dictationLocale("ur")).toBe("ur-IN");
  expect(dictationLocale("fr")).toBeNull();
  expect(dictationLocale("constructor")).toBeNull();
});

test("the recogniser listens in the answer language chosen, or Auto's language of the question", () => {
  expect(dictationLocale(resolvedLanguage("hi", "", OFFERED).code)).toBe("hi-IN");
  expect(dictationLocale(resolvedLanguage("hi", "Why alum?", OFFERED).code)).toBe("hi-IN");
  expect(dictationLocale(resolvedLanguage("auto", "தமிழ் நாட்டில் பட்டு", OFFERED).code)).toBe("ta-IN");
  expect(dictationLocale(resolvedLanguage("auto", "", OFFERED).code)).toBe("en-IN");
  expect(listeningLabel(HINDI)).toBe("Listening · हिन्दी");
});

test("the recogniser is the standard class, else the prefixed one, else none", () => {
  class Standard {}
  class Prefixed {}
  expect(recogniserClass({ SpeechRecognition: Standard, webkitSpeechRecognition: Prefixed })).toBe(Standard);
  expect(recogniserClass({ webkitSpeechRecognition: Prefixed })).toBe(Prefixed);
  expect(recogniserClass({})).toBeNull();
  expect(recogniserClass({ SpeechRecognition: "not a class" })).toBeNull();
});

test("settled words and words still being heard are kept apart and joined by single spaces", () => {
  const heard = heardText([
    { transcript: "how is ", isFinal: true },
    { transcript: " the red fixed", isFinal: true },
    { transcript: " in ajrakh", isFinal: false },
    { transcript: "   ", isFinal: false }
  ]);
  expect(heard).toEqual({ settled: "how is the red fixed", pending: "in ajrakh" });
  expect(spokenText(heard)).toBe("how is the red fixed in ajrakh");
  expect(spokenText({ settled: "", pending: "अजरख" })).toBe("अजरख");
});

test("dictation adds to what was typed and never passes the question limit", () => {
  expect(composeQuestion("In Kutch, ", "why alum", 1000)).toBe("In Kutch, why alum");
  expect(composeQuestion("", "why alum", 1000)).toBe("why alum");
  expect(composeQuestion("abc", "defgh", 6)).toBe("abc de");
});

test("a session listens continuously with live words and reports what it heard, failed with and ended", () => {
  FakeRecogniser.made = [];
  const heard: string[] = [];
  const failures: string[] = [];
  let ended = 0;
  const session = openDictation(FakeRecogniser as unknown as RecogniserClass, "hi-IN", {
    onHeard: (found) => heard.push(spokenText(found)),
    onFailure: (code) => failures.push(code),
    onEnd: () => (ended += 1)
  });
  const made = FakeRecogniser.made[0];
  expect([made.lang, made.continuous, made.interimResults, made.maxAlternatives]).toEqual(["hi-IN", true, true, 1]);
  expect(made.calls).toEqual(["start"]);
  made.onresult?.(resultsEvent(result("अजरख में", false)));
  made.onresult?.(resultsEvent(result("अजरख में", true), result("लाल रंग", false)));
  made.onerror?.({ error: "no-speech" });
  made.onend?.();
  session.stop();
  session.abort();
  expect(heard).toEqual(["अजरख में", "अजरख में लाल रंग"]);
  expect(failures).toEqual(["no-speech"]);
  expect(ended).toBe(1);
  expect(made.calls).toEqual(["start", "stop", "abort"]);
});

test("a refused language hides dictation for it; our own abort says nothing; the rest say what to do", () => {
  expect(dictationFailure("language-not-supported", ODIA)).toEqual({ message: "This browser can't take dictation in Odia.", refusesLanguage: true });
  expect(dictationFailure("aborted", HINDI)).toBeNull();
  expect(dictationFailure("not-allowed", HINDI)).toEqual({ message: "Allow the microphone to dictate.", refusesLanguage: false });
  expect(dictationFailure("service-not-allowed", HINDI)?.message).toBe("Allow the microphone to dictate.");
  expect(dictationFailure("audio-capture", HINDI)?.message).toBe("No microphone found.");
  expect(dictationFailure("network", HINDI)?.message).toBe("Dictation needs a connection.");
  expect(dictationFailure("no-speech", HINDI)?.message).toBe("Didn't catch that. Try again.");
  expect(dictationFailure("something-new", HINDI)?.message).toBe(DICTATION_STOPPED);
  const codes = ["language-not-supported", "not-allowed", "audio-capture", "network", "no-speech", "something-new"];
  for (const code of codes) expect(gapCopyFindings(dictationFailure(code, ODIA)?.message ?? "")).toEqual([]);
});

test("a browser that can say which languages it hears is asked; one that cannot is trusted until it refuses", async () => {
  const asked: unknown[] = [];
  const answering = (status: string) =>
    Object.assign(class {}, {
      available: async (options: { langs: string[] }) => {
        asked.push(options);
        return status;
      }
    }) as unknown as RecogniserClass;
  expect(await localeOffered(class {} as unknown as RecogniserClass, "or-IN")).toBe(true);
  expect(await localeOffered(answering("available"), "hi-IN")).toBe(true);
  expect(await localeOffered(answering("downloadable"), "ta-IN")).toBe(true);
  expect(await localeOffered(answering("unavailable"), "or-IN")).toBe(false);
  expect(asked).toEqual([{ langs: ["hi-IN"] }, { langs: ["ta-IN"] }, { langs: ["or-IN"] }]);
  const failing = Object.assign(class {}, {
    available: async () => {
      throw new TypeError("bad options");
    }
  }) as unknown as RecogniserClass;
  const checked = await quietly(() => localeOffered(failing, "hi-IN"));
  expect(checked.value).toBe(true);
  expect(String(checked.logged[0])).toContain("bad options");
});
