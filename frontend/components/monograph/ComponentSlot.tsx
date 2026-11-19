import { BundleView, NestedSlots, SLOT_CLASS, SlotRoot } from "@/components/monograph/BundleView";
import { COMPONENT_VIEWS } from "@/components/monograph/componentViews";
import type { MonographDocument } from "@/lib/monographDocument";
import { bundleSources } from "@/lib/monographRenderKit";
import { componentBundles, placedComponents, slotId } from "@/lib/monographRenderLayout";

export type SlotDrawing = "view" | "fragment" | "none";

export function slotDrawing(document: MonographDocument, label: string): SlotDrawing {
  const component = document.content.components.find((found) => found.label === label);
  if (!component) return "none";
  if (Object.hasOwn(document.specs, label) && COMPONENT_VIEWS[component.kind]) return "view";
  if (Object.hasOwn(document.fragments, label)) return "fragment";
  return "none";
}

export function ComponentSlot({ document, label }: { document: MonographDocument; label: string }) {
  const drawing = slotDrawing(document, label);
  if (drawing === "view") {
    const bundles = componentBundles(document, label);
    return (
      <SlotRoot sources={bundleSources(document, bundles)} bundles={bundles}>
        <BundleView label={label} />
      </SlotRoot>
    );
  }
  if (drawing === "none") return null;
  const nested = placedComponents(document, label);
  const bundles = Object.assign({}, ...nested.map((found) => componentBundles(document, found)));
  return (
    <>
      <div className={SLOT_CLASS} id={slotId(label)} data-component={label} dangerouslySetInnerHTML={{ __html: document.fragments[label] }} />
      {nested.length ? (
        <SlotRoot sources={bundleSources(document, bundles)} bundles={bundles}>
          <NestedSlots hostId={slotId(label)} />
        </SlotRoot>
      ) : null}
    </>
  );
}
