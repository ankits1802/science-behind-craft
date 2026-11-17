import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { CitationProvider, type CitationLookup } from "@/components/answer/CitationContext";
import { ExplainerReadingProvider, type ExplainerReading } from "@/components/answer/ExplainerReading";
import { ExplainerSentence } from "@/components/answer/ExplainerSentence";
import { ExplainerView } from "@/components/answer/ExplainerView";
import { ImageStrip } from "@/components/answer/ImageStrip";
import { AuthProvider } from "@/components/AuthProvider";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ENGLISH } from "@/lib/answerLanguages";
import { splitSseBuffer } from "@/lib/answerStream";
import type { ExplainerBlock, ImagesBlock, ProseBlock } from "@/lib/explainerContract";
import { askingExplainer, reduceExplainer, type ExplainerState } from "@/lib/explainerState";
import { explainerEventOf, type ExplainerEvent } from "@/lib/explainerStream";
import type { UnderstoodPart } from "@/lib/explainerView";

const ROOT = join(__dirname, "..", "..");
const read = (...parts: string[]) => readFileSync(join(ROOT, ...parts), "utf8");

function researched(): ExplainerState {
  const { blocks } = splitSseBuffer(read("shared", "answer-stream.research.golden.sse"));
  const events = blocks.map(explainerEventOf).filter((event): event is ExplainerEvent => event !== null);
  return events.reduce(reduceExplainer, askingExplainer("Why does alum keep Ajrakh red?", "en"));
}

function blockOf<K extends ExplainerBlock["kind"]>(state: ExplainerState, kind: K): Extract<ExplainerBlock, { kind: K }> {
  const found = state.sections.flatMap((section) => section.blocks).find((block) => block.kind === kind);
  if (!found) throw new Error(`the researched golden streams a ${kind} block`);
  return found as Extract<ExplainerBlock, { kind: K }>;
}

function reading(onTerm: ExplainerReading["onTerm"]): ExplainerReading {
  return { language: ENGLISH, original: false, hiddenTerms: new Set(), onTerm, listen: null };
}

function withReading(child: ReactElement, onTerm: ExplainerReading["onTerm"] = () => undefined): string {
  const lookup: CitationLookup = { numbers: new Map(), sourcesById: new Map(), onOpen: () => undefined };
  return renderToStaticMarkup(createElement(ExplainerReadingProvider, { value: reading(onTerm) }, createElement(CitationProvider, { value: lookup }, child)));
}

function attributes(html: string, name: string): string[] {
  return [...html.matchAll(new RegExp(`${name}="([^"]*)"`, "g"))].map((found) => found[1]);
}

test("a streamed images block is drawn as a credited inline picture and a credited link card", () => {
  const images: ImagesBlock = blockOf(researched(), "images");
  const html = renderToStaticMarkup(createElement(ImageStrip, { block: images }));
  expect(attributes(html, "data-display")).toEqual(["INLINE", "LINK_CARD"]);
  expect(html.match(/referrerpolicy="no-referrer"/gi)?.length).toBe(images.items.length);
  expect(html).not.toMatch(/referrerpolicy="(?!no-referrer")/i);
  for (const item of images.items) {
    expect(attributes(html, "href")).toContain(item.media.pageUrl);
    expect(attributes(html, "src")).toContain(item.media.imageUrl);
  }
  expect(html).toContain("A. Dyer");
  expect(html).toContain("CC BY-SA 4.0");
  expect(html).toContain("Crafts Museum");
  expect(html).toContain("Red alizarin lake after many washes");
});

test("a streamed sentence underlines its server-marked terms as buttons that open the term sheet", () => {
  const prose: ProseBlock = blockOf(researched(), "prose");
  const [first] = prose.sentences;
  expect(first.terms).toEqual([
    { text: "Alum", termKey: "alum" },
    { text: "alizarin", termKey: "alizarin" },
    { text: "cotton", termKey: "cotton" }
  ]);
  const html = withReading(createElement(ExplainerSentence, { sentence: first }));
  const buttons = [...html.matchAll(/<button[^>]*data-testid="term-span"[^>]*>(.*?)<\/button>/g)].map((found) => found[1].replace(/<[^>]+>/g, ""));
  expect(buttons).toEqual(["Alum", "alizarin", "cotton"]);
  expect(html.replace(/<[^>]+>/g, "")).toContain("Alum is the mordant that binds alizarin to cotton.");
  const view = read("frontend", "components", "answer", "ExplainerView.tsx");
  expect(view).toContain("onTerm: terms.open");
  expect(view).toContain("<TermSheet span={terms.span}");
  expect(read("frontend", "components", "answer", "ExplainerSentence.tsx")).toContain("onClick={() => reading.onTerm(term)}");
  expect(read("frontend", "components", "answer", "TermSheet.tsx")).toContain("open={span !== null && !missing}");
});

test("the whole explainer view draws the researched answer with its pictures and terms", () => {
  const view = createElement(ExplainerView, {
    state: researched(),
    streaming: false,
    languages: [ENGLISH],
    depthLabel: "Detailed",
    change: { parts: new Set<UnderstoodPart>(), onChange: () => undefined },
    listenLanguages: [],
    onFollowUp: null,
    onFreshResearch: null
  });
  const html = renderToStaticMarkup(createElement(AuthProvider, null, createElement(ThemeProvider, null, view)));
  expect(attributes(html, "data-kind")).toEqual(["prose", "images"]);
  expect(html).toContain('data-testid="image-strip"');
  expect(html.match(/data-testid="term-span"/g)?.length).toBe(4);
});
