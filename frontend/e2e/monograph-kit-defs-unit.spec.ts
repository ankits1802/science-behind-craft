import { expect, test } from "@playwright/test";

import { KIT_DEFS } from "@/generated/kitDefs";
import { defsByScope, referencedIds, usedDefs, type KitDef } from "@/lib/monographKitDefs";

const def = (scope: string | null, markup: string): KitDef => ({ scope, markup });

const DEFS: Record<string, KitDef> = {
  "ag-C": def("chem", '<radialGradient id="ag-C"><stop offset="0"/></radialGradient>'),
  "chem-weave": def("chem", '<pattern id="chem-weave"><path d="M0 3 L3 0"/></pattern>'),
  "tile-1": def("pt", '<pattern id="tile-1"><rect fill="url(#chem-weave)"/></pattern>'),
  unused: def("pt", '<pattern id="unused"><path d="M0 0"/></pattern>')
};

test("a drawing's references are found by url() and by a use element's href, never by a page anchor", () => {
  expect(referencedIds('<circle fill="url(#ag-C)"/><use href="#tile-1"/><use href=\'#ag-H\'/>')).toEqual(["ag-C", "tile-1", "ag-H"]);
  expect(referencedIds("plain text with # and url(nothing)")).toEqual([]);
  expect(referencedIds('<a href="#sources">Sources</a>')).toEqual([]);
  expect(referencedIds(JSON.stringify({ tag: "use", attrs: { href: "#hd-plait", "xlink:href": "#vlg-base" } }))).toEqual(["hd-plait", "vlg-base"]);
});

test("a page carries only the definitions its drawings use, following one definition into another", () => {
  const spec = JSON.stringify({ atoms: [{ fill: "url(#ag-C)" }, { fill: "url(#ag-C)" }], cloth: { tag: "use", attrs: { href: "#tile-1" } }, missing: "url(#not-defined)" });
  expect(usedDefs([spec], DEFS)).toEqual([DEFS["ag-C"], DEFS["tile-1"], DEFS["chem-weave"]]);
  expect(usedDefs(["no drawing here"], DEFS)).toEqual([]);
});

test("a definition the page already holds is never added twice", () => {
  const fragment = '<svg><defs><radialGradient id="ag-C"/></defs><circle fill="url(#ag-C)"/><rect fill="url(#chem-weave)"/></svg>';
  expect(usedDefs([fragment], DEFS)).toEqual([DEFS["chem-weave"]]);
  expect(usedDefs([JSON.stringify({ tag: "pattern", attrs: { id: "tile-1" } }), "url(#tile-1)"], DEFS)).toEqual([]);
});

test("definitions are grouped by the scope whose colours they read", () => {
  expect(defsByScope([DEFS["ag-C"], DEFS["tile-1"], DEFS["chem-weave"]])).toEqual([
    { scope: "chem", markup: [DEFS["ag-C"].markup, DEFS["chem-weave"].markup] },
    { scope: "pt", markup: [DEFS["tile-1"].markup] }
  ]);
});

test("the atom gradients a borrowed molecule fills its atoms with are kept in the chemistry scope, whose colours they read", () => {
  for (const id of ["ag-C", "ag-H", "ag-N", "ag-O"]) {
    expect(KIT_DEFS[id].markup, id).toContain(`id="${id}"`);
    expect(KIT_DEFS[id].scope, id).toBe("chem");
  }
});
