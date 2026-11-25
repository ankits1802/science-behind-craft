import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { AuthProvider } from "../components/AuthProvider";
import { MonographPage } from "../components/monograph/MonographPage";
import { ThemeProvider } from "../components/ThemeProvider";
import { kindPreviewDocument } from "../lib/kindPreview";
import type { MonographDocument } from "../lib/monographDocument";
import { mastheadFetchedFirst, mastheadPictureLabel, shownPage } from "../lib/monographShownPage";

import { HERO } from "./generatedMonographFixture";
import { filedKindFixtures, phoneFixtureDocument } from "./phoneFixturePage";

const FETCHED_FIRST = /<link rel="preload" as="image"[^>]*fetchPriority="high"[^>]*>/g;
const PHONE_WIDTH = "/_next/image?url=%2Fmonographs%2Fkutch-ajrakh%2Fimg%2Fajrakh-cloth-field-and-borders.jpg&amp;w=960&amp;q=80 960w";

function markup(document: MonographDocument): string {
  return renderToStaticMarkup(createElement(AuthProvider, null, createElement(ThemeProvider, null, createElement(MonographPage, { document }))));
}

test("a page whose masthead holds a photograph asks for it first from the document's head, at the widths a phone chooses from", () => {
  const preloads = markup(phoneFixtureDocument()).match(FETCHED_FIRST) ?? [];
  expect(preloads).toHaveLength(1);
  expect(preloads[0]).toContain(PHONE_WIDTH);
  expect(preloads[0]).toContain('imageSizes="100vw"');
});

test("a page whose masthead has no photograph asks for no picture first", () => {
  expect(markup(kindPreviewDocument(filedKindFixtures())).match(FETCHED_FIRST)).toBeNull();
});

test("the masthead's picture is fetched first whatever its spec asked, and no other spec changes", () => {
  const document = phoneFixtureDocument();
  const { plan } = shownPage(document);
  expect(mastheadPictureLabel(plan)).toBe(HERO);
  expect(document.specs[HERO].picture).toMatchObject({ loading: null, fetchPriority: null });
  const first = mastheadFetchedFirst(document, plan);
  expect(first.specs[HERO].picture).toEqual({ ...(document.specs[HERO].picture as object), loading: null, fetchPriority: "high" });
  for (const label of Object.keys(document.specs).filter((found) => found !== HERO)) expect(first.specs[label]).toBe(document.specs[label]);
  const bare = kindPreviewDocument(filedKindFixtures());
  expect(mastheadFetchedFirst(bare, shownPage(bare).plan)).toBe(bare);
});
