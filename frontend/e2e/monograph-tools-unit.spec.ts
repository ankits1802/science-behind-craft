import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { nearBlocksLoaded } from "../components/answer/nearBlock";
import { AuthProvider } from "../components/AuthProvider";
import { ComponentSlot } from "../components/monograph/ComponentSlot";
import { askNextHref } from "../components/monograph/kinds/tools/AskNextView";
import { writingLine } from "../components/monograph/kinds/tools/GeneratorView";
import { quizScore, quizVerdict } from "../components/monograph/kinds/tools/QuizView";
import { MonographPage } from "../components/monograph/MonographPage";
import { ThemeProvider } from "../components/ThemeProvider";
import { pagePlan } from "../lib/monographRenderLayout";
import { generatorSpecShape, languageSwitchSpecShape, quizSpecShape, TOOL_KINDS, TOOL_SPEC_SHAPES, type ToolKind } from "../lib/componentSpecsTools";
import type { MonographDocument } from "../lib/monographDocument";
import { parseMonographDocument } from "../lib/monographDocumentShape";
import { parseShape } from "../lib/shape";

test.beforeAll(() => nearBlocksLoaded());

const AJRAKH = join(__dirname, "..", "..", "backend", "app", "data", "monographs", "Kutch-Ajrakh");
const LABEL = {
  explainer: "kutch-ajrakh/overview/how-to-read-citations",
  quiz: "kutch-ajrakh/overview/check-yourself-quiz",
  ask: "kutch-ajrakh/overview/ask-next",
  languages: "kutch-ajrakh/overview/answer-in-hindi-and-urdu",
  level: "kutch-ajrakh/chemistry/student-version",
  generator: "kutch-ajrakh/overview/watch-it-being-made"
} as const;

function ajrakhDocument(): MonographDocument {
  const content = JSON.parse(readFileSync(join(AJRAKH, "content.json"), "utf8"));
  const specs = Object.fromEntries(
    readdirSync(join(AJRAKH, "specs")).map((file) => [file.replace(/\.json$/, "").replace(/__/g, "/"), JSON.parse(readFileSync(join(AJRAKH, "specs", file), "utf8"))])
  );
  return parseMonographDocument({ schemaVersion: 1, subjectKind: "craft", subjectSlug: "Kutch-Ajrakh", language: "en", title: "Kutch Ajrakh", version: 3, content, specs, fragments: {}, shell: null, pageUrl: "https://kalavigyan.example/crafts/Kutch-Ajrakh" });
}

const document = ajrakhDocument();
const slot = (label: string) => renderToStaticMarkup(createElement(AuthProvider, null, createElement(ComponentSlot, { document, label })));
const kindOf = (label: string) => document.content.components.find((component) => component.label === label)?.kind as ToolKind;

test("Ajrakh's content and each extracted tool spec parse with the frontend's shapes", () => {
  const labels = Object.keys(document.specs).filter((label) => (TOOL_KINDS as readonly string[]).includes(kindOf(label)));
  expect(labels.map(kindOf).sort()).toEqual([...TOOL_KINDS].sort());
  for (const label of labels) expect(() => parseShape(TOOL_SPEC_SHAPES[kindOf(label)], document.specs[label]), label).not.toThrow();
});

test("a tool spec that is ambiguous or broken is refused", () => {
  const quiz = structuredClone(document.specs[LABEL.quiz]) as { questions: { choices: { right: boolean }[] }[] };
  quiz.questions[0].choices[1].right = true;
  expect(() => parseShape(quizSpecShape, quiz)).toThrow(/exactly one right choice/);
  const languages = structuredClone(document.specs[LABEL.languages]) as { panels: unknown[] };
  languages.panels.reverse();
  expect(() => parseShape(languageSwitchSpecShape, languages)).toThrow(/one panel for each language/);
  const generator = structuredClone(document.specs[LABEL.generator]) as { sections: Record<string, unknown>[] };
  generator.sections[0].title = "Both";
  expect(() => parseShape(generatorSpecShape, generator)).toThrow(/title or titleUnit, exactly one/);
});

test("the explainer draws its two quote cards from sources six and eleven with their keyed marks", () => {
  const html = slot(LABEL.explainer);
  expect(html).toContain('<section class="howcite"');
  expect(html).toContain('<b><span class="mk a" aria-hidden="true">a</span>6</b><strong>Ajrakh: An Introduction</strong><span>Khan, Sahapedia</span>');
  expect(html).toContain("<b>11</b><strong>Ajrakh: From Caste Dress to Catwalk</strong>");
  expect(html).toContain("B · reputable reference");
  expect(html.match(/<li>/g)).toHaveLength(4);
});

test("the quiz opens on its first of three questions with three words to choose from", () => {
  const html = slot(LABEL.quiz);
  expect(html).toContain("Question 1 of 3");
  expect(html).toContain("Printed on harde-treated cloth,");
  expect([...html.matchAll(/class="quiz-opt"[^>]*><i>([a-z]+)<\/i>/g)].map((found) => found[1])).toEqual(["kut", "gach", "saaj"]);
  const spec = parseShape(quizSpecShape, document.specs[LABEL.quiz]);
  expect(quizVerdict(spec.questions[0], "kut")).toBe("Right: kut.");
  expect(quizVerdict(spec.questions[0], "gach")).toBe("Not quite: the word is kut.");
  expect(quizScore([true, false, true], 3)).toBe("2 of 3");
});

test("asking next goes to the app's ask screen, through sign-in for a reader who is signed out", () => {
  expect(askNextHref(true, "Kutch-Ajrakh", "Why lime?")).toBe("/ask?q=Why+lime%3F&craft=Kutch-Ajrakh");
  expect(askNextHref(false, "Kutch-Ajrakh", "Why lime?")).toContain(encodeURIComponent("/ask?q=Why+lime%3F&craft=Kutch-Ajrakh"));
  const html = slot(LABEL.ask);
  expect(html.match(/<li>/g)).toHaveLength(6);
  expect(html).toContain('<span class="aq">How is the indigo vat prepared and kept working for ajrakh?</span>');
});

test("the language switch offers English, Hindi and Urdu, showing English and keeping the others ready", () => {
  const html = slot(LABEL.languages);
  expect([...html.matchAll(/aria-pressed="(true|false)" lang="([a-z]+)"/g)].map((found) => `${found[2]}:${found[1]}`)).toEqual(["en:true", "hi:false", "ur:false"]);
  expect(html).toContain('<div class="lang-panel" data-ui-lang="ur" lang="ur" dir="rtl" hidden="">');
  expect(html).toContain('<span class="t-caption" role="status">English · the answer as written</span>');
  expect(html).not.toContain("lang-seg");
});

test("the student version opens to its title and lede", () => {
  const html = slot(LABEL.level);
  expect(html).toContain('<span class="kv-alt-s">The student version</span>');
  expect(html).toContain("Student, 14 to 17");
});

test("the Ajrakh document draws the approved page's thirteen chapters in order, numbered 1 to 12 after the answer", () => {
  const plan = pagePlan(document);
  expect(plan.chapters.map((chapter) => chapter.key)).toEqual(["answer", "cloth", "made", "chemistry", "why-kachchh", "history", "market", "what-if", "people", "kin", "reading", "media", "sources"]);
  expect(plan.chapters.map((chapter) => chapter.number)).toEqual([null, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]);
  const labels = Object.fromEntries(plan.chapters.map((chapter) => [chapter.key, chapter.label]));
  expect(labels).toMatchObject({ made: "How it is made", chemistry: "The chemistry", "why-kachchh": "Why Kachchh", history: "History and trade", "what-if": "What if", people: "People and voices", reading: "Reading tools", media: "Pictures, video and film", sources: "Sources" });
  expect(plan.masthead).toEqual({ kicker: "u0001", standfirst: ["u0003"], lede: "u0004", picture: "kutch-ajrakh/design/cloth-field-and-borders-photo" });
  const html = renderToStaticMarkup(createElement(AuthProvider, null, createElement(ThemeProvider, null, createElement(MonographPage, { document }))));
  expect(html.match(/<h1/g)).toHaveLength(1);
  expect(html.match(/class="kv-src-li"/g)).toHaveLength(Object.keys(document.content.sources).length);
});

test("the generator rests finished: seven written sections, its media rail and a replay to start", () => {
  const html = slot(LABEL.generator);
  expect(html.match(/<article class="gsec"/g)).toHaveLength(7);
  expect(html.match(/data-state="done"/g)).toHaveLength(7);
  expect(html).toContain("Answer written");
  expect(html).toContain("From Sindh to Kutch at a king&#x27;s invitation");
  expect(html.match(/class="jt"/g)).toHaveLength(9);
  expect(writingLine(0, 7)).toBe("Writing section 1 of 7");
  expect(writingLine(7, 7)).toBe("Writing section 7 of 7");
});
