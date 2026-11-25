import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { FRONTEND } from "./moduleGraph";

const APP = join(FRONTEND, "app");
const COMPONENTS = join(FRONTEND, "components");
const SHEET_IMPORT = /^@import "(\.[^"]+\.css)";$/gm;

function imported(sheet: string): string[] {
  return [...readFileSync(join(APP, sheet), "utf8").matchAll(SHEET_IMPORT)].map((found) => relative(FRONTEND, resolve(APP, found[1])).replace(/\\/g, "/"));
}

function componentSheets(folder: string = COMPONENTS): string[] {
  return readdirSync(folder, { withFileTypes: true }).flatMap((entry) => {
    const found = join(folder, entry.name);
    if (entry.isDirectory()) return componentSheets(found);
    return entry.name.endsWith(".css") ? [relative(FRONTEND, found).replace(/\\/g, "/")] : [];
  });
}

test("the views' stylesheets load as one sheet of the root layout, in the order the craft page drew them as separate files", () => {
  expect(imported("component-views.css")).toEqual([
    "components/map/place-context/placeContext.css",
    "components/monograph/kinds/general/general.css",
    "components/monograph/kinds/general/themes.css",
    "components/artkit/artkit.css",
    "components/monograph/authoredShell.css",
    "components/monograph/documentLanguage.css",
    "components/monograph/documentPage.css",
    "components/monograph/kinds/blocks/answerBlock.css"
  ]);
  expect(readFileSync(join(APP, "layout.tsx"), "utf8")).toContain('import "./globals.css";\nimport "./component-views.css";');
});

test("every stylesheet under components is held by exactly one of the layout's two sheets", () => {
  const held = [...imported("globals.css").filter((sheet) => sheet.startsWith("components/")), ...imported("component-views.css")];
  expect([...held].sort()).toEqual(componentSheets().sort());
  expect(new Set(held).size).toBe(held.length);
});
