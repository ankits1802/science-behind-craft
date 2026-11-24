import { KitFigure } from "@/components/artkit/KitFigure";
import { kitIds } from "@/components/artkit/kitIds";
import { GeneralFigure } from "@/components/monograph/kinds/general/GeneralFigure";
import { parsedSpec } from "@/lib/componentSpecsGeneral";
import { kitDiagramShape } from "@/lib/componentSpecsKit";
import type { ComponentViewProps } from "@/lib/componentViewContract";

export function KitDiagramView({ component, spec, renderUnit, unitText }: ComponentViewProps) {
  const diagram = parsedSpec(kitDiagramShape, spec);
  if (!diagram) return null;
  const titleId = `${kitIds(component.label).base}-t`;
  return (
    <GeneralFigure kind="diagram" head={{ title: diagram.head.title, caption: diagram.head.caption ?? null }} titleId={titleId} renderUnit={renderUnit}>
      <div className="grid gap-3" data-testid="kit-diagram">
        <KitFigure spec={diagram} label={component.label} renderUnit={renderUnit} unitText={unitText} />
        <p className="kv-kit-alt">{renderUnit(diagram.alt)}</p>
      </div>
    </GeneralFigure>
  );
}
