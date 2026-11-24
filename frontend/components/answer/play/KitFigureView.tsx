import { CitationChips } from "@/components/answer/CitationContext";
import { KitFigure } from "@/components/artkit/KitFigure";
import { kitLabelOf, type KitFigureBlock } from "@/lib/explainerKit";

const FIGURE = "kv-figure m-0 grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3";
export const KIT_FIGURE_KICKER = "Diagram";

export function KitFigureView({ block }: { block: KitFigureBlock }) {
  const titleId = `${block.id}-title`;
  const unitText = (ref: string) => kitLabelOf(block, ref)?.text ?? "";
  const renderUnit = (ref: string) => {
    const found = kitLabelOf(block, ref);
    if (!found) return null;
    return (
      <>
        {found.text}
        <CitationChips citations={found.citations ?? []} />
      </>
    );
  };
  return (
    <figure className={FIGURE} aria-labelledby={titleId} data-testid="kit-figure" data-layout={block.diagram.layout} lang="en">
      <header className="grid min-w-0 gap-1">
        <p className="kicker">{KIT_FIGURE_KICKER}</p>
        <h3 id={titleId} className="break-words font-reading text-h3 text-ink-1">
          {unitText(block.diagram.head.title)}
        </h3>
      </header>
      <KitFigure spec={block.diagram} label={`answer-${block.id}`} renderUnit={renderUnit} unitText={unitText} />
      <p className="kv-kit-alt">{unitText(block.diagram.alt)}</p>
    </figure>
  );
}
