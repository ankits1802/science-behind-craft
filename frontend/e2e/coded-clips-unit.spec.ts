import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { nearBlocksLoaded } from "@/components/answer/nearBlock";
import { COMPONENT_VIEWS } from "@/components/monograph/componentViews";
import { ClipStills, CLIP_STILL_MISSING } from "@/components/review/ClipStills";
import { CLIP_LINK_PATH, clipAddresses, clipEnds, clipLinks, clipStillHref } from "@/lib/codedClips";
import { clipSource, codedFrameCsp, codedFrameDocument, codedFramePieces, FILMS_ELEMENT_ID } from "@/lib/codedFigureFrame";
import { codedFigureShape, codedWords, ONE_FILM_SOURCE, type CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";
import type { ComponentView } from "@/lib/componentViewContract";
import type { FrameLook } from "@/lib/sandboxFrame";
import { parseShape, ShapeError } from "@/lib/shape";

test.beforeAll(() => nearBlocksLoaded());

const REPO = join(__dirname, "..", "..");
const ORIGIN = "https://kalavigyan.example";
const FIXTURE = JSON.parse(readFileSync(join(REPO, "backend", "app", "data", "kind_fixtures", "coded_figure.json"), "utf8")) as { label: string; spec: Record<string, unknown>; units: Record<string, { text: string }> };
const said = (ref: string) => FIXTURE.units[ref]?.text ?? "";
const CLIP = "2d4f6a8c-0e1b-4c3d-9e5f-7a9b1c3d5e7f";
const CREDIT = "AI video, made with veo-3.1-fast on 2026-11-21";
const OBJECT = "https://kv-media.s3.ap-south-1.amazonaws.com/media/craft/eeee/KalaVigyan_Generated-Video_Video_Step-04.mp4";
const SIGNED = `${OBJECT}?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=300&X-Amz-Signature=abc123`;
const CODE = String(FIXTURE.spec.code).replace("<ul ", '<video data-film="dip" muted></video><ul ');
const CLIPPED = parseShape(codedFigureShape, { ...FIXTURE.spec, code: CODE, films: [{ key: "dip", clip: CLIP, credit: CREDIT }] });
const WORDS = codedWords(CLIPPED, said);
const LOOK: FrameLook = { tokens: { "--font-ui": "sans-serif" }, reducedMotion: true };

function mediaSources(csp: string): string[] {
  const directive = csp.split(";").map((part) => part.trim()).find((part) => part.startsWith("media-src "));
  return directive ? directive.slice("media-src ".length).split(/\s+/) : [];
}

function filmsOf(head: string): Record<string, string> {
  const found = new RegExp(`<script type="application/json" id="${FILMS_ELEMENT_ID}">(.*?)</script>`).exec(head);
  return JSON.parse(found?.[1] ?? "{}") as Record<string, string>;
}

test("a film is a file the site serves or a media-store clip, never both and never neither", () => {
  expect(CLIPPED.films).toEqual([{ key: "dip", clip: CLIP, credit: CREDIT }]);
  const both = { key: "dip", src: "/monographs/kit/films/dip.mp4", clip: CLIP };
  for (const film of [both, { key: "dip" }]) {
    expect(() => parseShape(codedFigureShape, { ...FIXTURE.spec, films: [film] })).toThrow(ShapeError);
  }
  expect(() => parseShape(codedFigureShape, { ...FIXTURE.spec, films: [{ key: "dip", clip: "dip" }] })).toThrow(ShapeError);
  expect(ONE_FILM_SOURCE).toContain("one of the two");
});

test("the frame may reach the one signed clip and nothing else on its host", () => {
  const csp = codedFrameCsp(ORIGIN, CLIPPED, { dip: SIGNED });
  expect(mediaSources(csp)).toEqual([OBJECT]);
  expect(csp).not.toContain("X-Amz");
  expect(csp).not.toContain("*");
  expect(mediaSources(csp)).not.toContain("https://kv-media.s3.ap-south-1.amazonaws.com");
  const pieces = codedFramePieces({ origin: ORIGIN, figure: CLIPPED, words: WORDS, base: null, clips: { dip: SIGNED } });
  expect(filmsOf(pieces.head)).toEqual({ dip: SIGNED });
});

test("a clip with no signed link, a folder or a plain address is left out and the frame reaches no media", () => {
  expect(mediaSources(codedFrameCsp(ORIGIN, CLIPPED))).toEqual(["'none'"]);
  expect(filmsOf(codedFramePieces({ origin: ORIGIN, figure: CLIPPED, words: WORDS, base: null }).head)).toEqual({});
  expect(clipSource("https://kv-media.s3.ap-south-1.amazonaws.com/media/craft/")).toBeNull();
  expect(clipSource(OBJECT.replace("https:", "http:"))).toBeNull();
  expect(clipSource("not an address")).toBeNull();
  expect(mediaSources(codedFrameCsp(ORIGIN, CLIPPED, { dip: "https://kv-media.example/media/" }))).toEqual(["'none'"]);
});

test("a figure without clips keeps its media sources as before", () => {
  const plain = parseShape(codedFigureShape, FIXTURE.spec);
  expect(mediaSources(codedFrameCsp(ORIGIN, plain))).toEqual(["'none'"]);
  const served: CodedFigureSpec = { ...plain, films: [{ key: "dip", src: "/monographs/kit/films/dip.mp4" }] };
  expect(mediaSources(codedFrameCsp(ORIGIN, served))).toEqual([`${ORIGIN}/monographs/kit/films/dip.mp4`]);
  expect(filmsOf(codedFramePieces({ origin: ORIGIN, figure: served, words: WORDS, base: null }).head)).toEqual({ dip: `${ORIGIN}/monographs/kit/films/dip.mp4` });
});

test("each clip's link is asked for at its own address, and one that fails leaves only that film out", async () => {
  const figure: CodedFigureSpec = { ...CLIPPED, films: [{ key: "dip", clip: CLIP }, { key: "air", clip: "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d" }] };
  const asked: string[] = [];
  const links = await clipLinks(figure, async (clip) => {
    asked.push(CLIP_LINK_PATH(clip));
    if (clip !== CLIP) throw new Error("gone");
    return { url: SIGNED, expiresAt: "2026-11-26T10:05:00+00:00" };
  });
  expect(asked).toEqual([`/crafts/media/${CLIP}/film`, "/crafts/media/9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d/film"]);
  expect(links).toEqual({ dip: { url: SIGNED, expiresAt: "2026-11-26T10:05:00+00:00" } });
  expect(clipAddresses(links)).toEqual({ dip: SIGNED });
  expect(clipEnds(links)).toEqual({ dip: Date.parse("2026-11-26T10:05:00Z") });
});

test("in the frame the clip's element takes the signed address", async ({ page }) => {
  await page.route("**/*", (route) => route.abort());
  await page.setContent(codedFrameDocument({ origin: ORIGIN, figure: CLIPPED, words: WORDS, base: null, clips: { dip: SIGNED } }, LOOK));
  expect(await page.locator('video[data-film="dip"]').getAttribute("src")).toBe(SIGNED);
});

test("the clip's credit is drawn under the figure", () => {
  const component = { label: FIXTURE.label, chapter: "k1", anchor: "#k", kind: "coded_figure", title: "t", description: "d", field: "CHEMISTRY", fields: [], subjects: [] };
  const view = COMPONENT_VIEWS.coded_figure as ComponentView;
  const props = { component, spec: CLIPPED, unitRefs: Object.keys(FIXTURE.units), renderUnit: said, unitText: said, renderComponent: () => null };
  const html = renderToStaticMarkup(createElement(() => view(props)));
  expect(html).toContain(`<ul class="grid gap-1 font-ui text-caption text-ink-3" data-coded-credits=""><li>${CREDIT}</li></ul>`);
  const plain = { ...props, spec: parseShape(codedFigureShape, FIXTURE.spec) };
  expect(renderToStaticMarkup(createElement(() => view(plain)))).not.toContain("data-coded-credits");
});

test("the Review page shows each clip's still at the address paper reads it from, with its credit, and none for a figure without clips", () => {
  const html = renderToStaticMarkup(createElement(ClipStills, { figure: CLIPPED, alt: "The alloy darkens in the bath." }));
  expect(clipStillHref(CLIP)).toBe(`/api/crafts/media/${CLIP}/still`);
  expect(html).toContain(`<figure class="grid gap-1" data-clip-still="${CLIP}"><img src="/api/crafts/media/${CLIP}/still" alt="The alloy darkens in the bath."`);
  expect(html).toContain(`<figcaption class="font-ui text-caption text-ink-3">${CREDIT}</figcaption>`);
  expect(html).not.toContain(CLIP_STILL_MISSING);
  const plain = parseShape(codedFigureShape, FIXTURE.spec);
  expect(renderToStaticMarkup(createElement(ClipStills, { figure: plain, alt: "x" }))).toBe("");
  const served: CodedFigureSpec = { ...plain, films: [{ key: "dip", src: "/monographs/kit/films/dip.mp4" }] };
  expect(renderToStaticMarkup(createElement(ClipStills, { figure: served, alt: "x" }))).toBe("");
});
