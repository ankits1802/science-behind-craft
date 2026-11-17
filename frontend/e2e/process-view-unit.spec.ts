import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { renderChemistry } from "@/lib/chemistry";
import {
  checkedProcess,
  deltaHText,
  isUnbalanced,
  pubchemHref,
  readingClaim,
  readingRange,
  reactionSpoken,
  shownVariants,
  speciesNamesLine,
  STAGE_TYPE_LABEL,
  stageHasContent
} from "@/lib/processView";
import { craftProcessShape, type CraftProcess, type ProcessReaction, type StageCondition } from "@/lib/scienceContract";
import { parseShape, ShapeError } from "@/lib/shape";

const GOLDEN = join(__dirname, "..", "..", "shared", "science.process.golden.json");

function raw(): CraftProcess {
  return JSON.parse(readFileSync(GOLDEN, "utf8")) as CraftProcess;
}

function process(edit: (body: CraftProcess) => void = () => undefined): CraftProcess {
  const body = raw();
  edit(body);
  return checkedProcess(parseShape(craftProcessShape, body));
}

function stage(body: CraftProcess, ordinal: number) {
  const found = body.processes[0].stages.find((entry) => entry.ordinal === ordinal);
  if (!found) throw new Error(`no stage ${ordinal} in the golden process`);
  return found;
}

test("the Ajrakh timeline runs printing, mordanting, then dyeing", () => {
  const variants = shownVariants(process());
  expect(variants).toHaveLength(1);
  expect(variants[0].stages.map((entry) => STAGE_TYPE_LABEL[entry.stageType])).toEqual(["Printing", "Mordanting", "Dyeing"]);
  expect(variants[0].stages.every(stageHasContent)).toBe(true);
});

test("stages arriving out of order are shown by ordinal", () => {
  const body = process((value) => value.processes[0].stages.reverse());
  expect(shownVariants(body)[0].stages.map((entry) => entry.ordinal)).toEqual([5, 6, 11]);
});

test("each condition reading keeps its own claim and normalised range", () => {
  const body = process();
  const kut = stage(body, 5).conditions[0];
  expect(kut.readings.map((reading) => [reading.stated, readingRange(kut, reading)])).toEqual([
    ["ten to fifteen days", "240–360 h"],
    ["two weeks", "336 h"]
  ]);
  const second = readingClaim(kut, kut.readings[1]);
  expect(second.id).toBe("b7aa0b09-6cc4-5e29-9ab9-e865e4d9ddd3");
  expect(second.citations.map((citation) => citation.id)).toEqual(["2a47c2bc-5ea6-56ee-89e3-adcc38723ca8"]);
  const red = stage(body, 11).conditions[0];
  expect(readingRange(red, red.readings[0])).toBe("≤ 4 h");
});

test("temperature and pH readings use their own units", () => {
  const condition = (quantity: StageCondition["quantity"], unit: string): StageCondition => ({ ...stage(raw(), 5).conditions[0], quantity, unit });
  const reading = (min: number | null, max: number | null) => ({ ...stage(raw(), 5).conditions[0].readings[0], min, max });
  expect(readingRange(condition("TEMPERATURE", "°C"), reading(60, 60))).toBe("60 °C");
  expect(readingRange(condition("TEMPERATURE", "°C"), reading(60, null))).toBe("≥ 60 °C");
  expect(readingRange(condition("PH", "pH"), reading(4, 4.8))).toBe("pH 4.0–4.8");
  expect(readingRange(condition("PH", "pH"), reading(null, null))).toBeNull();
});

test("a balanced reaction reads as names with its coefficients", () => {
  const iron = stage(process(), 5).reactions[0];
  expect(iron.equation).toBe("Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2");
  expect(reactionSpoken(iron)).toBe("Iron + 2 Acetic acid gives Iron(II) acetate + Hydrogen");
  expect(speciesNamesLine(iron)).toBe("Iron · Acetic acid → Iron(II) acetate · Hydrogen");
  expect(isUnbalanced(iron)).toBe(false);
});

test("a species-only reaction has no equation and no cap", () => {
  const lake = stage(process(), 11).reactions[0];
  expect(lake.equation).toBeNull();
  expect(isUnbalanced(lake)).toBe(false);
  expect(reactionSpoken(lake)).toBe("Aluminium from the alum mordant + Alizarin gives Aluminium-alizarin lake");
});

test("an unbalanced equation is flagged by its level reason", () => {
  const body = process((value) => {
    const reaction = value.processes[0].stages[0].reactions[0] as ProcessReaction;
    reaction.balanced = false;
    reaction.checkerVersion = null;
    reaction.equation = "Fe + CH3COOH -> Fe(CH3COO)2 + H2";
    reaction.species = reaction.species.map((species) => ({ ...species, coefficient: null }));
    reaction.level = "HYPOTHESIS";
    reaction.levelReason = "unbalanced";
  });
  const reaction = stage(body, 5).reactions[0];
  expect(isUnbalanced(reaction)).toBe(true);
  expect(reactionSpoken(reaction)).toBe("Iron + Acetic acid gives Iron(II) acetate + Hydrogen");
});

test("a cited enthalpy is shown with its sign", () => {
  const body = process((value) => {
    value.processes[0].stages[0].reactions[0].deltaH = { kjPerMol: -57.3, claimId: "c407fde1-3c40-5c81-8a5e-320317aacf9d" };
  });
  expect(stage(body, 5).reactions[0].deltaH?.kjPerMol).toBe(-57.3);
  expect(deltaHText(-57.3)).toBe("ΔH −57.3 kJ/mol");
});

test("the client refuses a reading or enthalpy whose claim is not listed", () => {
  expect(() =>
    process((value) => {
      value.processes[0].stages[0].reactions[0].deltaH = { kjPerMol: -1, claimId: "00000000-0000-4000-8000-000000000000" };
    })
  ).toThrow(ShapeError);
  expect(() =>
    process((value) => {
      value.processes[0].stages[0].conditions[0].readings[1].claimId = "00000000-0000-4000-8000-000000000000";
    })
  ).toThrow(ShapeError);
});

test("no processes, or processes without stages, leave nothing to draw", () => {
  expect(shownVariants(process((value) => (value.processes = [])))).toEqual([]);
  expect(shownVariants(process((value) => (value.processes[0].stages = [])))).toEqual([]);
});

test("a stage with no cited claims is sent bare and drawn as no source found", () => {
  const body = process((value) => {
    const bare = value.processes[0].stages[1];
    bare.level = "UNAVAILABLE";
    bare.claims = [];
    bare.materials = [];
  });
  const bare = stage(body, 6);
  expect(bare.level).toBe("UNAVAILABLE");
  expect(stageHasContent(bare)).toBe(false);
});

test("PubChem links only for a real compound id", () => {
  expect(pubchemHref(6342)).toBe("https://pubchem.ncbi.nlm.nih.gov/compound/6342");
  expect(pubchemHref(null)).toBeNull();
  expect(pubchemHref(0)).toBeNull();
});

test("every equation and formula the server sends renders through mhchem", () => {
  const reactions = process().processes.flatMap((variant) => variant.stages.flatMap((entry) => entry.reactions));
  const sources = [
    ...reactions.flatMap((reaction) => (reaction.equation ? [reaction.equation] : [])),
    ...reactions.flatMap((reaction) => reaction.species.flatMap((species) => (species.formula ? [species.formula] : [])))
  ];
  expect(sources).toEqual(["Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2", "Fe", "CH3COOH", "Fe(CH3COO)2", "H2", "Al^3+", "C14H8O4"]);
  for (const source of sources) {
    const html = renderChemistry(source, false);
    expect(html, source).toContain("katex");
    expect(html, source).not.toContain("katex-error");
  }
});
