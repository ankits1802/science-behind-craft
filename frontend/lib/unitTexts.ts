import { nodesText } from "@/lib/monographRender";
import type { ComponentBundle } from "@/lib/monographRenderLayout";

export function unitTexts(bundle: ComponentBundle | undefined): (ref: string) => string {
  return (ref) => {
    const unit = bundle?.units[ref];
    return unit ? nodesText(unit.nodes) : "";
  };
}
