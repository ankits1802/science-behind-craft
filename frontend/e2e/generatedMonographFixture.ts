import type { MonographComponent, MonographDocument, MonographNode, MonographUnit } from "../lib/monographDocument";

export const HERO = "bagh-print/pictures/i02";
export const COMMONS_FILE = "https://upload.wikimedia.org/wikipedia/commons/a/ab/I02.jpg";
export const CAPTION = "The printed field, washed in the river";
export const CREDIT = "Photo: A. Printer, CC BY-SA 4.0, via Wikimedia Commons";
export const LEDE = "Bagh print is block printed on the Baghini river.";

const unit = (chapter: string, tag: string, nodes: MonographNode[]): MonographUnit => ({ chapter, tag, field: null, nodes, claimIds: [] });

const cited = (text: string, last: string, key: string, sources: string[]): MonographNode => ({ m: "s", c: [text, { m: "cite", key, g: sources, c: [last] }] });

const hero: MonographComponent = {
  label: HERO,
  chapter: "opening",
  anchor: "#bagh-print--pictures--i02",
  kind: "picture_plate",
  title: CAPTION,
  description: `A picture for Bagh Print: ${CAPTION}.`,
  field: "OVERVIEW",
  fields: [],
  subjects: ["craft:Bagh-Print"]
};

const MASTHEAD = ["masthead-kicker", "masthead-title", "label-place-term", "label-place", "label-gi-term", "label-gi"];

const layout = (chapter: string, kind: "unit" | "component", ref: string, within: string | null = null) => ({ chapter, kind, ref, within });

export function generatedDocument(): MonographDocument {
  return {
    schemaVersion: 1,
    subjectKind: "craft",
    subjectSlug: "Bagh-Print",
    language: "en",
    title: "Bagh Print",
    version: 5,
    pageUrl: "https://kalavigyan.example/crafts/Bagh-Print",
    shell: null,
    content: {
      schemaVersion: 1,
      craftSlug: "Bagh-Print",
      sources: {
        g1: { number: 1, title: "Bagh survey", fullTitle: null, publisher: "Survey of crafts", year: 2020, grade: "A", url: "https://example.org/bagh", extra: null, dossierSourceId: null },
        g2: { number: 2, title: "Alum on cotton", fullTitle: null, publisher: null, year: 2019, grade: "B", url: null, extra: null, dossierSourceId: null }
      },
      citations: {
        "overview-1": [{ source: "g1", locator: "p. 2", quote: "Block printed by the river." }],
        "chemistry-1": [
          { source: "g2", locator: "p. 1", quote: "Alum fixes red." },
          { source: "g1", locator: null, quote: null }
        ]
      },
      citationClaims: {},
      data: {},
      units: {
        u9001: unit("opening", "span", [CAPTION]),
        u9002: unit("opening", "span", [CREDIT]),
        "masthead-kicker": unit("opening", "p", [
          { m: "span", c: ["Monograph"] },
          { m: "span", c: ["Textiles · Hand block printing"] }
        ]),
        "masthead-title": unit("opening", "h1", ["Bagh Print"]),
        "label-place-term": unit("opening", "dt", ["Place"]),
        "label-place": unit("opening", "dd", ["Madhya Pradesh"]),
        "label-gi-term": unit("opening", "dt", ["GI"]),
        "label-gi": unit("opening", "dd", ["Registered geographical indication"]),
        "overview-1": unit("opening", "p", [cited("Bagh print is block printed on the Baghini ", "river.", "overview-1", ["g1"])]),
        "chapter-chem": unit("chem", "h2", ["The chemistry"]),
        "chemistry-1": unit("chem", "p", [cited("Alum fixes the madder ", "red.", "chemistry-1", ["g2", "g1"])]),
        "chapter-sources": unit("sources", "h2", ["Sources"])
      },
      components: [hero],
      layout: [
        layout("opening", "component", HERO),
        layout("opening", "unit", "u9001", HERO),
        layout("opening", "unit", "u9002", HERO),
        ...MASTHEAD.map((ref) => layout("opening", "unit", ref)),
        layout("opening", "unit", "overview-1"),
        layout("chem", "unit", "chapter-chem"),
        layout("chem", "unit", "chemistry-1"),
        layout("sources", "unit", "chapter-sources")
      ]
    },
    specs: {
      [HERO]: {
        setting: "figure",
        picture: { src: COMMONS_FILE, width: 1600, height: 1200, alt: "Picture I02", loading: null, fetchPriority: null, decoding: null, focal: { x: 0.2, y: 0.2, width: 0.6, height: 0.6 } },
        figure: { classes: ["plate"], crop: null, captions: [{ unit: "u9001", look: false }], credit: "u9002" },
        row: null,
        pull: null,
        opener: null,
        masthead: null
      }
    },
    fragments: {}
  };
}

export const MASTHEAD_UNITS = MASTHEAD;
