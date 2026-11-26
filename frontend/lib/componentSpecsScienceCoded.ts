import { headShape, svgMarkup, themesShape, type DrawingThemes, type GeneralHead } from "@/lib/componentSpecsGeneral";
import { unitRef } from "@/lib/componentSpecsScienceParts";
import { integer, list, matching, number, object, oneOf, optional, type Shape } from "@/lib/shape";

export const CODED_FIGURE_KIND = "coded_figure";
export const CODED_LIBRARIES = ["d3", "three"] as const;
export const MAP_LAYERS = ["states", "districts", "rivers", "relief"] as const;

export type CodedLibrary = (typeof CODED_LIBRARIES)[number];
export type MapLayer = (typeof MAP_LAYERS)[number];
export type CodedValue = { key: string; value: number; reading: string };
export type CodedText = { key: string; unit: string };
export type CodedFilm = { key: string; src: string };
export type CodedMap = { layers: MapLayer[]; districts: number[] };
export type CodedFigureSpec = {
  head: GeneralHead;
  alt: string;
  code: string;
  values: CodedValue[];
  texts: CodedText[];
  libraries?: CodedLibrary[];
  map?: CodedMap;
  films?: CodedFilm[];
  still?: string;
  themes?: DrawingThemes;
};

const codeKey = matching(/^[a-z][a-z0-9_]{0,39}$/, "a key of the code's own");
const filmSource = matching(/^\/monographs\/[A-Za-z0-9][A-Za-z0-9._/-]*\.(mp4|webm)$/, "a film the site serves");

export const codedFigureShape: Shape<CodedFigureSpec> = object<CodedFigureSpec>({
  head: headShape,
  alt: unitRef,
  code: matching(/\S/, "the figure's code"),
  values: list(object<CodedValue>({ key: codeKey, value: number, reading: unitRef })),
  texts: list(object<CodedText>({ key: codeKey, unit: unitRef })),
  libraries: optional(list(oneOf(CODED_LIBRARIES))),
  map: optional(object<CodedMap>({ layers: list(oneOf(MAP_LAYERS)), districts: list(integer) })),
  films: optional(list(object<CodedFilm>({ key: codeKey, src: filmSource }))),
  still: optional(svgMarkup),
  themes: optional(themesShape)
});

export function codedWords(figure: CodedFigureSpec, said: (ref: string) => string): Record<string, string> {
  const words: Record<string, string> = {};
  for (const text of figure.texts) words[text.key] = said(text.unit);
  return words;
}

export function codedValues(figure: CodedFigureSpec): { key: string; value: number }[] {
  return figure.values.map((value) => ({ key: value.key, value: value.value }));
}

const TEXT_UNIT = /<(text|tspan)\b([^>]*?)\bdata-unit="([a-z][a-z0-9_]*)"([^>]*?)\s*\/>/g;
const ESCAPED: Readonly<Record<string, string>> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" };

export function wordedStill(svg: string, words: Readonly<Record<string, string>>): string {
  return svg.replace(TEXT_UNIT, (found, tag: string, before: string, key: string, after: string) => {
    if (!Object.hasOwn(words, key)) return found;
    const said = words[key].replace(/[&<>"]/g, (character) => ESCAPED[character]);
    return `<${tag}${before}data-unit="${key}"${after}>${said}</${tag}>`;
  });
}
