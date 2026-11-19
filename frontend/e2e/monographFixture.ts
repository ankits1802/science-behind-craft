import type { MonographComponent, MonographDocument, MonographUnit } from "../lib/monographDocument";

export const PICTURE = "test-craft/design/cloth-photo";
export const QUIZ = "test-craft/overview/check-yourself";
export const LIST = "test-craft/overview/source-status";
export const ASK = "test-craft/overview/ask-next";

const component = (label: string, chapter: string, kind: string, anchor: string): MonographComponent => ({
  label,
  chapter,
  anchor,
  kind,
  title: label.split("/").pop() ?? label,
  description: "A component of the test page.",
  field: "OVERVIEW",
  fields: [],
  subjects: []
});

const unit = (chapter: string, tag: string, nodes: MonographUnit["nodes"]): MonographUnit => ({ chapter, tag, field: null, nodes, claimIds: [] });

const cited = (text: string, last: string, key: string, sources: string[]) => ({ m: "s", c: [text, { m: "cite", key, g: sources, c: [last] }] });

export const UNITS: Record<string, MonographUnit> = {
  u0001: unit("answer", "p", [{ m: "span", c: ["Monograph"] }]),
  u0002: unit("answer", "p", ["The short answer"]),
  u0003: unit("answer", "p", [cited("Test cloth is printed with a resist and dyed in ", "indigo.", "t:1", ["g2", "g1"])]),
  u0004: unit("answer", "p", ["Photo: test"]),
  u0005: unit("made", "p", ["1"]),
  u0006: unit("made", "p", ["How it is made"]),
  u0007: unit("made", "h2", ["Printed, then dyed"]),
  u0008: unit("made", "p", [cited("The cloth is printed twice before the ", "vat.", "t:2", ["g1"])]),
  u0009: unit("made", "li", [{ m: "b", c: ["1"] }, { m: "span", c: ["Test journal, 2023"] }]),
  u0010: unit("made", "p", ["Two steps"]),
  u0011: unit("made", "li", ["Scour the cloth"]),
  u0012: unit("made", "li", ["Print the resist"]),
  u0013: unit("made", "h3", ["Check yourself"]),
  u0014: unit("made", "p", ["Each blank was a word in one of the cited sentences."]),
  u0015: unit("made", "p", ["3 of 3"]),
  u0016: unit("made", "p", ["Choose the word that fills the blank."]),
  u0017: unit("sources", "p", ["2"]),
  u0018: unit("sources", "p", ["Sources"]),
  u0019: unit("sources", "h2", ["Every source, numbered once"]),
  u0020: unit("sources", "h3", ["Government records"]),
  u0021: unit("sources", "h3", ["Scholarship"])
};

const layout = (chapter: string, kind: "unit" | "component", ref: string, within: string | null = null) => ({ chapter, kind, ref, within });

export const QUIZ_SPEC = {
  title: "u0013",
  kicker: "One question from this answer",
  dek: "u0014",
  score: "u0015",
  status: "u0016",
  nextLabel: "Next question",
  questions: [
    {
      before: "The cloth is printed twice before the",
      after: ".",
      cite: { key: "t:2", sources: ["g1"] },
      choices: [
        { term: "vat", right: true, sentence: [cited("The cloth is printed twice before the ", "vat.", "t:2", ["g1"])] },
        { term: "kiln", right: false, sentence: ["Nothing is fired."] }
      ]
    }
  ]
};

export function fixtureDocument(): MonographDocument {
  return {
    schemaVersion: 1,
    subjectKind: "craft",
    subjectSlug: "Test-Craft",
    title: "Test Craft",
    version: 2,
    pageUrl: "https://kalavigyan.example/crafts/Test-Craft",
    content: {
      schemaVersion: 1,
      craftSlug: "Test-Craft",
      sources: {
        g1: { number: 1, title: "Test journal", fullTitle: "The test journal, volume 1", publisher: "Test Registry", year: 2023, grade: "A", url: "https://example.org/journal", extra: null, dossierSourceId: "S01" },
        g2: { number: 2, title: "Test book", fullTitle: null, publisher: null, year: null, grade: "B", url: null, extra: null, dossierSourceId: null }
      },
      citations: { "t:1": [{ source: "g1", locator: "p. 2", quote: "Printed with a resist." }], "t:2": [{ source: "g1", locator: null, quote: null }] },
      citationClaims: {},
      data: { "kv-data": { quiz: [] }, "loose-data": { note: "</script>" } },
      units: UNITS,
      components: [component(PICTURE, "answer", "picture_plate", "#photo"), component(QUIZ, "made", "quiz", "#quiz-block"), component(LIST, "sources", "source_list", "#status"), component(ASK, "sources", "ask_next", "[class=\"asknext\"]")],
      layout: [
        layout("answer", "unit", "u0001"),
        layout("answer", "unit", "u0002"),
        layout("answer", "unit", "u0003"),
        layout("answer", "component", PICTURE),
        layout("answer", "unit", "u0004", PICTURE),
        ...["u0005", "u0006", "u0007", "u0008", "u0009", "u0010", "u0011", "u0012"].map((ref) => layout("made", "unit", ref)),
        layout("made", "component", QUIZ),
        ...["u0013", "u0014", "u0015", "u0016"].map((ref) => layout("made", "unit", ref, QUIZ)),
        ...["u0017", "u0018", "u0019"].map((ref) => layout("sources", "unit", ref)),
        layout("sources", "component", LIST),
        layout("sources", "component", ASK),
        layout("sources", "unit", "u0020"),
        layout("sources", "unit", "u0021")
      ]
    },
    specs: { [QUIZ]: QUIZ_SPEC, [ASK]: { craft: "Test-Craft", action: "Ask", questions: ["Why indigo?"] } },
    fragments: {
      [PICTURE]: '<figure class="plate" id="photo"><img src="/x.jpg" alt="A cloth"><figcaption><p class="credit">Photo: test</p></figcaption></figure>',
      [LIST]: `<div id="status" class="kv-src-status" role="status"></div><kv-slot component="${ASK}"></kv-slot>`
    }
  };
}
