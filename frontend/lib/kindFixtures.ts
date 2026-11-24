import { dictionary, integer, list, matching, nullable, object, oneOf, optional, parseShape, ShapeError, text, type Shape } from "@/lib/shape";
import { UNIT_REF } from "@/lib/unitIds";

export type FixtureUnit = { text: string; claims: string[] };
export type FixtureQuote = { source: string; locator: string; quote: string };
export type FixtureFact = { text: string; quotes: FixtureQuote[] };
export type FixtureSource = { title: string; publisher: string | null; year: number | null; url: string | null; reliability: string | null };
export type KindFixture = {
  schemaVersion: 1;
  kind: string;
  craft: string;
  craftName: string;
  label: string;
  title: string;
  description: string;
  field: string;
  within: string | null;
  spec: Record<string, unknown>;
  units: Record<string, FixtureUnit>;
  facts: Record<string, FixtureFact>;
  sources: Record<string, FixtureSource>;
  placed?: Record<string, unknown>;
};

const ANY_KEY = /^[\w-]+$/;
const record: Shape<Record<string, unknown>> = {
  expected: "an object",
  parse(value, path) {
    if (typeof value !== "object" || value === null || Array.isArray(value)) throw new ShapeError(path, "an object");
    return value as Record<string, unknown>;
  }
};

const fixtureShape: Shape<KindFixture> = object<KindFixture>({
  schemaVersion: oneOf([1] as const),
  kind: text,
  craft: text,
  craftName: text,
  label: matching(/^[a-z0-9]+(-[a-z0-9]+)*(\/[a-z0-9]+(-[a-z0-9]+)*){2,}$/, "a component label"),
  title: text,
  description: text,
  field: text,
  within: nullable(text),
  spec: record,
  units: dictionary(UNIT_REF, object<FixtureUnit>({ text, claims: list(text) })),
  facts: dictionary(ANY_KEY, object<FixtureFact>({ text, quotes: list(object<FixtureQuote>({ source: text, locator: text, quote: text }), 1) })),
  sources: dictionary(ANY_KEY, object<FixtureSource>({ title: text, publisher: nullable(text), year: nullable(integer), url: nullable(text), reliability: nullable(text) })),
  placed: optional(record)
});

export const KIND_FIXTURES_PATH = "/design/kind-fixtures";

const fixturesShape: Shape<{ fixtures: KindFixture[] }> = object<{ fixtures: KindFixture[] }>({ fixtures: list(fixtureShape, 1) });

export function placedSpec(spec: Record<string, unknown>, placed: Record<string, unknown> | undefined): Record<string, unknown> {
  if (!placed) return spec;
  const found = Array.isArray(placed.places) ? placed.places : [];
  const places = Array.isArray(spec.places) ? spec.places.map((place, at) => ({ ...(place as Record<string, unknown>), found: found[at] })) : spec.places;
  return { ...spec, ...placed, places };
}

export function parseKindFixtures(body: unknown): KindFixture[] {
  return parseShape(fixturesShape, body).fixtures.map(({ placed, ...fixture }) => ({ ...fixture, spec: placedSpec(fixture.spec, placed) }));
}
