import type { MonographDocument } from "@/lib/monographDocument";
import { numberedDocument } from "@/lib/monographRenderFigures";
import { pagePlan, type PagePlan } from "@/lib/monographRenderLayout";
import { placedPlan } from "@/lib/monographRenderNear";

const FETCHED_FIRST = { loading: null, fetchPriority: "high" } as const;

export function mastheadPictureLabel(plan: PagePlan): string | null {
  return plan.label?.picture ?? plan.masthead.picture;
}

export function mastheadFetchedFirst(document: MonographDocument, plan: PagePlan): MonographDocument {
  const label = mastheadPictureLabel(plan);
  const spec = label !== null && Object.hasOwn(document.specs, label) ? document.specs[label] : null;
  const picture = spec?.picture;
  if (label === null || spec === null || typeof picture !== "object" || picture === null) return document;
  return { ...document, specs: { ...document.specs, [label]: { ...spec, picture: { ...picture, ...FETCHED_FIRST } } } };
}

export function shownPage(document: MonographDocument): { document: MonographDocument; plan: PagePlan } {
  const plan = placedPlan(document, pagePlan(document));
  return { document: mastheadFetchedFirst(numberedDocument(document, plan), plan), plan };
}
