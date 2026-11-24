import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { parseKindFixtures, type KindFixture } from "../lib/kindFixtures";
import { kindPreviewDocument } from "../lib/kindPreview";
import type { MonographDocument, MonographNode } from "../lib/monographDocument";

import { generatedDocument, HERO } from "./generatedMonographFixture";

export const PHONE_FIXTURE_CRAFT = "Phone-Fixtures";
export const PHONE_FIXTURE_PICTURE = { src: "/monographs/kutch-ajrakh/img/ajrakh-cloth-field-and-borders.jpg", width: 1280, height: 960 } as const;

const FIXTURES_DIR = join(__dirname, "..", "..", "backend", "app", "data", "kind_fixtures");
const OPENING = "opening";
const ALT = "Two Kutch artisans hold up a whole ajrakh to show its repeated central field and its borders.";
const CAPTION: MonographNode[] = ["An ajrakh held up to show its repeated field and its borders."];
const CREDIT: MonographNode[] = ["Photo: ", { m: "link", href: "https://commons.wikimedia.org/wiki/File:Ajrak_Craft.jpeg", c: ["Visdaviva, CC BY-SA 3.0, via Wikimedia Commons"] }];

export function filedKindFixtures(): KindFixture[] {
  const filed = readdirSync(FIXTURES_DIR)
    .filter((name) => name.endsWith(".json"))
    .sort()
    .map((name) => JSON.parse(readFileSync(join(FIXTURES_DIR, name), "utf8")) as unknown);
  return parseKindFixtures({ fixtures: filed });
}

function openingPicture(): Pick<MonographDocument, "content" | "specs"> {
  const generated = generatedDocument();
  const spec = generated.specs[HERO];
  const figure = spec.figure as { captions: { unit: string }[]; credit: string };
  const [caption, credit] = [generated.content.units[figure.captions[0].unit], generated.content.units[figure.credit]];
  const units = { [figure.captions[0].unit]: { ...caption, nodes: CAPTION }, [figure.credit]: { ...credit, nodes: CREDIT } };
  const layout = generated.content.layout.filter((entry) => entry.ref === HERO || entry.within === HERO);
  const picture = { ...(spec.picture as Record<string, unknown>), ...PHONE_FIXTURE_PICTURE, alt: ALT };
  const components = generated.content.components.filter((component) => component.label === HERO);
  return { content: { ...generated.content, units, layout, components }, specs: { [HERO]: { ...spec, picture } } };
}

export function phoneFixtureDocument(fixtures: readonly KindFixture[] = filedKindFixtures()): MonographDocument {
  const kinds = kindPreviewDocument(fixtures);
  const picture = openingPicture();
  const [opening, rest] = [kinds.content.layout.filter((entry) => entry.chapter === OPENING), kinds.content.layout.filter((entry) => entry.chapter !== OPENING)];
  const content = {
    ...kinds.content,
    craftSlug: PHONE_FIXTURE_CRAFT,
    units: { ...kinds.content.units, ...picture.content.units },
    components: [...picture.content.components, ...kinds.content.components],
    layout: [...picture.content.layout, ...opening, ...rest]
  };
  return { ...kinds, subjectSlug: PHONE_FIXTURE_CRAFT, pageUrl: `https://kalavigyan.vercel.app/crafts/${PHONE_FIXTURE_CRAFT}`, content, specs: { ...picture.specs, ...kinds.specs } };
}
