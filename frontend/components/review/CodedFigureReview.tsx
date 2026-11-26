import { CodedFrame } from "@/components/monograph/kinds/science/CodedFrame";
import { CodedStill } from "@/components/monograph/kinds/science/CodedStill";
import { parsedSpec } from "@/lib/componentSpecsGeneral";
import { CODED_FIGURE_KIND, codedFigureShape, codedWords } from "@/lib/componentSpecsScienceCoded";
import type { MonographDocument } from "@/lib/monographDocument";
import { nodesText } from "@/lib/monographRender";

export const CODED_STILL_HEADING = "Its still, for paper and the first paint";
export const CODED_RUN_HEADING = "Running in its sandboxed frame";

export function CodedFigureReview({ document, label }: { document: MonographDocument; label: string }) {
  const component = document.content.components.find((found) => found.label === label);
  const figure = component?.kind === CODED_FIGURE_KIND ? parsedSpec(codedFigureShape, document.specs[label]) : null;
  if (!figure) return null;
  const said = (ref: string) => {
    const unit = document.content.units[ref];
    return unit ? nodesText(unit.nodes) : "";
  };
  const words = codedWords(figure, said);
  return (
    <div className="grid gap-5 lg:grid-cols-2" data-testid="coded-review">
      <section className="grid content-start gap-2">
        <h4 className="font-ui text-h4 text-ink-1">{CODED_STILL_HEADING}</h4>
        <CodedStill figure={figure} words={words} />
      </section>
      <section className="grid content-start gap-2">
        <h4 className="font-ui text-h4 text-ink-1">{CODED_RUN_HEADING}</h4>
        <CodedFrame title={said(figure.head.title)} figure={figure} words={words} />
      </section>
    </div>
  );
}
