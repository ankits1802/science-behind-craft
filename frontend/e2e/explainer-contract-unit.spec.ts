import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { splitSseBuffer } from "@/lib/answerStream";
import { explainerBlockShape, explainerSectionShape, explainerShape, termShape, type Explainer, type ExplainerBlock } from "@/lib/explainerContract";
import { parseExplainerStreamBlock, type ExplainerEvent } from "@/lib/explainerStream";
import { parseShape, ShapeError } from "@/lib/shape";

const SHARED = join(__dirname, "..", "..", "shared");

function golden(name: string): Record<string, unknown> {
  return JSON.parse(readFileSync(join(SHARED, name), "utf8"));
}

function explainer(): Explainer {
  return parseShape(explainerShape, golden("explainer.document.golden.json"));
}

function streamed(): ExplainerEvent[] {
  const { blocks, rest } = splitSseBuffer(readFileSync(join(SHARED, "explainer.stream.golden.sse"), "utf8"));
  expect(rest).toBe("");
  return blocks.map(parseExplainerStreamBlock).filter((event): event is ExplainerEvent => event !== null);
}

test("the client parses the explainer and the term as the backend writes them", () => {
  expect(explainer()).toEqual(golden("explainer.document.golden.json"));
  expect(parseShape(termShape, golden("explainer.term.golden.json"))).toEqual(golden("explainer.term.golden.json"));
});

test("the explainer for Kutch Ajrakh holds a ladder, images and a reused block", () => {
  const document = explainer();
  expect(document.understood).toMatchObject({ depth: "EXPERT", language: "en" });
  expect(document.sections.map((section) => [section.discipline, section.blocks.map((block) => block.kind)])).toEqual([
    ["PROCESS", ["process_ladder", "images"]],
    ["GEOGRAPHY", ["prose"]],
    ["CHEMISTRY", ["prose"]]
  ]);
  const reused = document.sections.flatMap((section) => section.blocks).filter((block) => block.reuse !== null);
  expect(reused.map((block) => block.id)).toEqual(["s2.b1"]);
  const ladder = document.sections[0].blocks[0];
  expect(ladder.kind === "process_ladder" && ladder.stages.map((stage) => stage.ordinal)).toEqual([4, 5, 6, 11]);
  const images = document.sections[0].blocks[1];
  expect(images.kind === "images" && images.items.map((item) => item.media.display)).toEqual(["INLINE", "LINK_CARD"]);
});

test("every citation names a listed source", () => {
  const document = explainer();
  const listed = new Set(document.sources.map((source) => source.id));
  const cited = JSON.stringify(document.sections).match(/"sourceId":"[0-9a-f-]{36}"/g) ?? [];
  expect(cited.length).toBeGreaterThan(0);
  for (const entry of cited) expect(listed.has(entry.slice(12, -1))).toBe(true);
});

test("the explainer stream parses, starts understood and ends done", () => {
  const events = streamed();
  expect(events[0].type).toBe("understood");
  expect(events.at(-1)?.type).toBe("done");
  expect(new Set(events.map((event) => event.type))).toEqual(
    new Set(["understood", "trail", "section_started", "source", "block", "section_done", "status", "section_state", "follow_ups", "done"])
  );
});

test("the streamed blocks are the explainer's blocks, section by section", () => {
  const bySection = new Map<string, ExplainerBlock[]>();
  for (const event of streamed()) {
    if (event.type === "block") bySection.set(event.data.sectionId, [...(bySection.get(event.data.sectionId) ?? []), event.data.block]);
  }
  for (const section of explainer().sections) expect(bySection.get(section.id)).toEqual(section.blocks);
});

test("a block kind that is not built yet is refused, not drawn", () => {
  const block = { id: "s3.b2", kind: "molecule_3d", version: 1, reuse: null, pubchemCid: 6293, name: "Alizarin", formula: "C14H8O4", sourceId: "x" };
  expect(() => parseShape(explainerBlockShape, block)).toThrow(ShapeError);
  const frame = `event: block\ndata: ${JSON.stringify({ sectionId: "s3", block })}`;
  expect(() => parseExplainerStreamBlock(frame)).toThrow(ShapeError);
});

test("unknown fields and events are refused or skipped", () => {
  const section = golden("explainer.document.golden.json").sections as Record<string, unknown>[];
  expect(() => parseShape(explainerSectionShape, { ...section[0], heading: "x" })).toThrow(ShapeError);
  expect(parseExplainerStreamBlock("event: match\ndata: {}")).toBeNull();
  expect(() => parseExplainerStreamBlock('event: section_state\ndata: {"sectionId":"s1","state":"READY"}')).toThrow(ShapeError);
  expect(() => parseExplainerStreamBlock("event: trail\ndata: not json")).toThrow(ShapeError);
});

test("an empty section says what it searched", () => {
  const section = (golden("explainer.document.golden.json").sections as Record<string, unknown>[])[2];
  const empty = parseShape(explainerSectionShape, { ...section, state: "EMPTY", blocks: [], searched: "Searched stored findings." });
  expect(empty.searched).toBe("Searched stored findings.");
});
