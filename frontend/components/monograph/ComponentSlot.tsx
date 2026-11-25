import { NestedSlots, SlotRoot } from "@/components/monograph/BundleView";
import { ComponentHome } from "@/components/monograph/ComponentHome";
import { COMPONENT_VIEWS } from "@/components/monograph/componentViews";
import { DrawnBundle } from "@/components/monograph/ServerBundle";
import { SLOT_CLASS } from "@/components/monograph/slotClass";
import type { MonographComponent, MonographDocument } from "@/lib/monographDocument";
import { slotPlacement, UNPLACED, type SlotPlacement } from "@/lib/monographPlacement";
import { bundleSources } from "@/lib/monographRenderKit";
import { componentBundles, placedComponents, slotId, specStrings } from "@/lib/monographRenderLayout";
import { appDrawn, componentHome, sizedHome } from "@/lib/monographScopes";
import { UNIT_REF } from "@/lib/unitIds";

export type SlotDrawing = "view" | "fragment" | "none";

export function unitsHeld(document: MonographDocument, label: string): boolean {
  return Object.values(componentBundles(document, label)).every((bundle) => specStrings(bundle.spec).every((value) => !UNIT_REF.test(value) || Object.hasOwn(document.content.units, value)));
}

export function slotDrawing(document: MonographDocument, label: string): SlotDrawing {
  const component = document.content.components.find((found) => found.label === label);
  if (!component) return "none";
  if (Object.hasOwn(document.specs, label) && COMPONENT_VIEWS[component.kind] && unitsHeld(document, label)) return "view";
  if (Object.hasOwn(document.fragments, label)) return "fragment";
  return "none";
}

type SlotProps = { document: MonographDocument; label: string; scoped?: boolean; beside?: boolean };
type DrawnSlot = { document: MonographDocument; component: MonographComponent; scoped: boolean; placing: SlotPlacement };

function specOf(document: MonographDocument, component: MonographComponent) {
  return Object.hasOwn(document.specs, component.label) ? document.specs[component.label] : null;
}

function homeOf(document: MonographDocument, component: MonographComponent, placing: SlotPlacement) {
  return sizedHome(componentHome(component.label, component.kind, specOf(document, component)), placing.size);
}

function ViewSlot({ document, component, scoped, placing }: DrawnSlot) {
  const bundles = componentBundles(document, component.label);
  const view = <DrawnBundle label={component.label} set={{ bundles, sources: bundleSources(document, bundles), bare: !appDrawn(component.kind, specOf(document, component)) }} />;
  if (!scoped) return view;
  return (
    <ComponentHome home={homeOf(document, component, placing)} label={component.label} kind={component.kind} placing={placing}>
      {view}
    </ComponentHome>
  );
}

function FragmentSlot({ document, component, scoped, placing }: DrawnSlot) {
  const label = component.label;
  const nested = placedComponents(document, label);
  const bundles = Object.assign({}, ...nested.map((found) => componentBundles(document, found)));
  const html = document.fragments[label];
  return (
    <>
      {scoped ? (
        <ComponentHome home={homeOf(document, component, placing)} label={label} kind={component.kind} placing={placing} fragment={{ id: slotId(label), html }} />
      ) : (
        <div className={SLOT_CLASS} id={slotId(label)} data-component={label} dangerouslySetInnerHTML={{ __html: html }} />
      )}
      {nested.length ? (
        <SlotRoot sources={bundleSources(document, bundles)} bundles={bundles} bare>
          <NestedSlots hostId={slotId(label)} />
        </SlotRoot>
      ) : null}
    </>
  );
}

export function ComponentSlot({ document, label, scoped = true, beside = false }: SlotProps) {
  const drawing = slotDrawing(document, label);
  const component = document.content.components.find((found) => found.label === label);
  if (drawing === "none" || !component) return null;
  const placing = scoped ? slotPlacement(document, label, beside) : UNPLACED;
  if (drawing === "view") return <ViewSlot document={document} component={component} scoped={scoped} placing={placing} />;
  return <FragmentSlot document={document} component={component} scoped={scoped} placing={placing} />;
}
