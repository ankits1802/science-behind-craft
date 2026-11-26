import { GeneralFigure } from "@/components/monograph/kinds/general/GeneralFigure";
import { parsedSpec } from "@/lib/componentSpecsGeneral";
import { clipFilms, CODED_FIGURE_KIND, codedFigureShape, codedWords, type CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";
import type { ComponentViewProps } from "@/lib/componentViewContract";

import { NearCodedFrame } from "./NearCodedFrame";

export const CODED_WORDS_SUMMARY = "Words and sources in this figure";

function idOf(label: string, part: string): string {
  return `cf-${label.replace(/[^a-z0-9]+/g, "-")}-${part}`;
}

function CodedWords({ figure, renderUnit }: { figure: CodedFigureSpec; renderUnit: ComponentViewProps["renderUnit"] }) {
  const refs = [...new Set([...figure.texts.map((text) => text.unit), ...figure.values.map((value) => value.reading)])].filter((ref) => ref !== figure.alt);
  if (!refs.length) return null;
  return (
    <details className="min-w-0" data-coded-words="">
      <summary className="kv-link inline-flex min-h-target cursor-pointer items-center font-ui text-ui">{CODED_WORDS_SUMMARY}</summary>
      <ul className="grid max-w-measure gap-1.5 pt-2 font-reading text-body-sm text-ink-1">
        {refs.map((ref) => (
          <li key={ref}>{renderUnit(ref)}</li>
        ))}
      </ul>
    </details>
  );
}

function ClipCredits({ figure }: { figure: CodedFigureSpec }) {
  const credited = clipFilms(figure).filter((film) => film.credit);
  if (!credited.length) return null;
  return (
    <ul className="grid gap-1 font-ui text-caption text-ink-3" data-coded-credits="">
      {credited.map((film) => (
        <li key={film.key}>{film.credit}</li>
      ))}
    </ul>
  );
}

export function CodedFigure({ component, spec, renderUnit, unitText }: ComponentViewProps) {
  const figure = parsedSpec(codedFigureShape, spec);
  if (!figure) return null;
  const said = unitText ?? (() => "");
  const words = codedWords(figure, said);
  const titleId = idOf(component.label, "title");
  const altId = idOf(component.label, "alt");
  return (
    <GeneralFigure kind={CODED_FIGURE_KIND} head={figure.head} titleId={titleId} renderUnit={renderUnit}>
      <div className="grid min-w-0 gap-2" data-coded="">
        <NearCodedFrame title={said(figure.head.title)} figure={figure} words={words} />
        <p id={altId} className="max-w-measure border-t border-rule pt-2 font-ui text-label text-ink-2">
          {renderUnit(figure.alt)}
        </p>
        <ClipCredits figure={figure} />
        <CodedWords figure={figure} renderUnit={renderUnit} />
      </div>
    </GeneralFigure>
  );
}
