import { expect, test } from "@playwright/test";
import { createElement, type ComponentProps, type ComponentType, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { AuthProvider } from "../components/AuthProvider";
import { AuthoredShell } from "../components/monograph/AuthoredShell";
import { MonographDocumentPage } from "../components/monograph/MonographDocumentPage";
import { MonographFrame } from "../components/monograph/MonographFrame";
import { MonographRail } from "../components/monograph/MonographRail";
import { MonographShellPage } from "../components/monograph/MonographShellPage";
import { pageDownloadItems } from "../components/monograph/PageDownloadList";
import { ThemeProvider } from "../components/ThemeProvider";
import type { MonographDocument } from "../lib/monographDocument";
import { railChapters } from "../lib/monographRenderLayout";
import { shownPage } from "../lib/monographShownPage";
import { PAGE_DOWNLOAD_LABEL, pageDownloads, pageSubject, type PageSubject } from "../lib/pageExport";

import { generatedDocument } from "./generatedMonographFixture";
import { eagerModules } from "./moduleGraph";
import { goldenDocument } from "./monographNative";

const Frame = MonographFrame as ComponentType<Omit<ComponentProps<typeof MonographFrame>, "children">>;
const provided = (element: ReactElement) => renderToStaticMarkup(createElement(AuthProvider, null, createElement(ThemeProvider, null, element)));
const DOWNLOAD = 'data-testid="page-download"';
const ROW = 'data-testid="page-download-row"';
const CITE = 'data-testid="cite-this"';
const MAIN = '<div id="kv-main">';

function subject(subjectKind: PageSubject["subjectKind"], subjectSlug: string, language = "en"): PageSubject {
  return { subjectKind, subjectSlug, language };
}

function mainClose(html: string, open: number): number {
  const tags = /<(\/?)div\b[^>]*>/g;
  tags.lastIndex = open;
  let depth = 0;
  for (let found = tags.exec(html); found; found = tags.exec(html)) {
    depth += found[1] ? -1 : 1;
    if (depth === 0) return found.index;
  }
  return -1;
}

function mainOf(html: string): string {
  const open = html.indexOf(MAIN);
  return html.slice(open, mainClose(html, open));
}

function page(document: MonographDocument, masthead = true): string {
  return provided(createElement(MonographDocumentPage, { document, masthead }));
}

test("a craft, a family and a category page each offer their PDF and their Word document", () => {
  expect(pageDownloads(subject("craft", "Kutch-Ajrakh"))).toEqual([
    { key: "pdf", label: "PDF", path: "/crafts/Kutch-Ajrakh/monograph/pdf" },
    { key: "docx", label: "Word document", path: "/crafts/Kutch-Ajrakh/monograph/docx" }
  ]);
  expect(pageDownloads(subject("family", "Other-Textiles")).map((link) => link.path)).toEqual(["/families/Other-Textiles/monograph/pdf", "/families/Other-Textiles/monograph/docx"]);
  expect(pageDownloads(subject("category", "Textiles", "hi")).map((link) => link.path)).toEqual(["/categories/Textiles/monograph/pdf?lang=hi", "/categories/Textiles/monograph/docx?lang=hi"]);
  expect(pageDownloadItems(subject("family", "Other-Textiles")).map((item) => [item.key, item.label])).toEqual([
    ["pdf", "PDF"],
    ["docx", "Word document"]
  ]);
});

test("the control takes only the page's kind, slug and language from its document", () => {
  expect(pageSubject(generatedDocument())).toEqual({ subjectKind: "craft", subjectSlug: "Bagh-Print", language: "en" });
});

test("a craft monograph draws Download in the cite block's row, beside Copy citation", () => {
  const html = page(generatedDocument());
  const cite = html.slice(html.indexOf(CITE));
  expect(cite).toMatch(new RegExp(`Copy citation</button><button [^>]*${DOWNLOAD}`));
  expect(cite).toContain(`>${PAGE_DOWNLOAD_LABEL}<`);
  expect(html.split(DOWNLOAD).length - 1).toBe(1);
  expect(html).not.toContain(ROW);
});

test("a family page and a category page, which have no cite block, draw Download alone where it would be", () => {
  for (const subjectKind of ["family", "category"] as const) {
    const html = page({ ...generatedDocument(), subjectKind }, subjectKind === "family");
    expect(html).not.toContain(CITE);
    expect(html).toContain(ROW);
    expect(html.split(DOWNLOAD).length - 1).toBe(1);
    const row = html.slice(html.indexOf(ROW));
    expect(row.indexOf(DOWNLOAD)).toBeGreaterThan(-1);
    expect(html.indexOf(ROW)).toBeGreaterThan(html.indexOf("Alum fixes the madder"));
  }
});

test("on Kutch Ajrakh the control sits after the approved page's main, which it leaves exactly as drawn", () => {
  const golden = goldenDocument();
  const html = provided(createElement(MonographShellPage, { document: golden }));
  const open = html.indexOf(MAIN);
  const close = mainClose(html, open);
  expect(open).toBeGreaterThan(-1);
  expect(html.indexOf(ROW)).toBeGreaterThan(close);
  expect(html.slice(open, close)).not.toContain("page-download");
  const { document, plan } = shownPage(golden);
  const before = provided(
    createElement(
      Frame,
      { document, given: golden, dataDeferred: false, languages: null },
      createElement(MonographRail, { chapters: railChapters(plan) }),
      createElement(AuthoredShell, { document, shell: document.shell ?? "" })
    )
  );
  expect(mainOf(html)).toBe(mainOf(before));
});

test("the page ships only Download's button; its list, popover and API client load when it is pressed", () => {
  const eager = [...eagerModules("@/components/monograph/PageDownload")];
  expect(eager).toContain("components/learn/DownloadTrigger.tsx");
  for (const lazy of ["components/monograph/PageDownloadList.tsx", "components/learn/DownloadList.tsx", "components/ui/AnchoredPopover.tsx", "lib/lessonApi.ts", "lib/api.ts"]) expect(eager).not.toContain(lazy);
  expect([...eagerModules("@/components/learn/DownloadMenu")]).toContain("components/learn/DownloadList.tsx");
});
