import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { nearBlocksLoaded } from "../components/answer/nearBlock";
import { AuthProvider } from "../components/AuthProvider";
import { ComponentSlot } from "../components/monograph/ComponentSlot";
import { MonographPage } from "../components/monograph/MonographPage";
import { ThemeProvider } from "../components/ThemeProvider";
import { pictureShape } from "../lib/componentSpecsPlates";
import { languageSwitchSpecShape, linkedSwitch } from "../lib/componentSpecsTools";
import type { MonographComponent, MonographDocument } from "../lib/monographDocument";
import { parseMonographDocument } from "../lib/monographDocumentShape";
import { pagePlan } from "../lib/monographRenderLayout";
import { parseShape } from "../lib/shape";

import { generatedDocument } from "./generatedMonographFixture";

test.beforeAll(() => nearBlocksLoaded());

const ASK = "bagh-print/reading/ask-next";
const LANGUAGES = "bagh-print/reading/page-languages";
const QUESTION = "How does alum fix the madder red?";
const SWITCH = {
  label: "Read this page in",
  options: [
    { lang: "en", name: "English", direction: "ltr", status: "English", href: "/crafts/Bagh-Print" },
    { lang: "hi", name: "हिन्दी", direction: "ltr", status: "Hindi", href: "/crafts/Bagh-Print/hi" },
    { lang: "ur", name: "اردو", direction: "rtl", status: "Urdu", href: "/crafts/Bagh-Print/ur" }
  ],
  panels: []
};

function tool(label: string, kind: string, title: string): MonographComponent {
  return { label, chapter: "reading", anchor: `#${label.replaceAll("/", "--")}`, kind, title, description: `${title} on the page.`, field: "OVERVIEW", fields: ["OVERVIEW"], subjects: ["craft:Bagh-Print"] };
}

function readingDocument(): MonographDocument {
  const base = generatedDocument();
  const sources = base.content.layout.filter((entry) => entry.chapter === "sources");
  const before = base.content.layout.filter((entry) => entry.chapter !== "sources");
  const reading = [
    { chapter: "reading", kind: "unit" as const, ref: "chapter-reading", within: null },
    { chapter: "reading", kind: "component" as const, ref: ASK, within: null },
    { chapter: "reading", kind: "component" as const, ref: LANGUAGES, within: null }
  ];
  return parseMonographDocument({
    ...base,
    content: {
      ...base.content,
      units: { ...base.content.units, "chapter-reading": { chapter: "reading", tag: "h2", field: null, nodes: ["Reading tools"], claimIds: [] } },
      components: [...base.content.components, tool(ASK, "ask_next", "Ask next"), tool(LANGUAGES, "language_switch", "Read this page in")],
      layout: [...before, ...reading, ...sources]
    },
    specs: { ...base.specs, [ASK]: { craft: "Bagh-Print", action: "Ask", questions: [QUESTION] }, [LANGUAGES]: SWITCH }
  });
}

const provided = (document: MonographDocument, label: string) => renderToStaticMarkup(createElement(AuthProvider, null, createElement(ComponentSlot, { document, label })));

test("a generated page's reading chapter stands before its sources, named Reading tools", () => {
  const plan = pagePlan(readingDocument());
  const keys = plan.chapters.map((chapter) => chapter.key);
  expect(keys.slice(-2)).toEqual(["reading", "sources"]);
  expect(plan.chapters.find((chapter) => chapter.key === "reading")?.label).toBe("Reading tools");
  const html = renderToStaticMarkup(createElement(AuthProvider, null, createElement(ThemeProvider, null, createElement(MonographPage, { document: readingDocument() }))));
  expect(html).toContain('id="reading"');
  expect(html).toContain(`<span class="aq">${QUESTION}</span>`);
});

test("the page's languages are links to the page in each, each name in its own script and direction", () => {
  const html = provided(readingDocument(), LANGUAGES);
  expect(html).toContain('aria-label="Read this page in"');
  expect(html).toContain('href="/crafts/Bagh-Print/hi"');
  expect(html).toContain('href="/crafts/Bagh-Print/ur"');
  expect(html).toContain('<span lang="ur" dir="rtl" data-script="Aran" class="ui">اردو</span>');
  expect(html).toContain('<span lang="hi" dir="ltr" data-script="Deva" class="ui">हिन्दी</span>');
  expect(html).not.toContain("lang-panel");
});

test("a switch is linked whole or shows its panels, never half of each", () => {
  const linked = parseShape(languageSwitchSpecShape, SWITCH);
  expect(linkedSwitch(linked)).toBe(true);
  const half = { ...SWITCH, options: [SWITCH.options[0], { ...SWITCH.options[1], href: undefined }] };
  expect(() => parseShape(languageSwitchSpecShape, JSON.parse(JSON.stringify(half)))).toThrow(/every option linked/);
  expect(() => parseShape(languageSwitchSpecShape, { ...SWITCH, english: "u0001" })).toThrow(/every option linked/);
  const away = { ...SWITCH, options: [{ ...SWITCH.options[0], href: "https://elsewhere.example/crafts/Bagh-Print" }, SWITCH.options[1]] };
  expect(() => parseShape(languageSwitchSpecShape, away)).toThrow();
});

test("a field portal photograph is a picture the page may draw, and no other API path is", () => {
  const picture = { src: "/api/field-voices/images/5e1d0000-0000-4000-8000-0000000000f1", width: 1600, height: 1200, alt: "A printer at work", loading: null, fetchPriority: null, decoding: null };
  expect(parseShape(pictureShape, picture).src).toBe(picture.src);
  expect(() => parseShape(pictureShape, { ...picture, src: "/api/field-voices/audio/5e1d0000-0000-4000-8000-0000000000f1" })).toThrow();
});
