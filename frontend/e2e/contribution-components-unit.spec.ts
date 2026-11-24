import { expect, test } from "@playwright/test";

import {
  componentBody,
  componentFromTask,
  componentProblems,
  componentResultShape,
  consideredAfter,
  emptyComponent,
  extendedDraft,
  replacingDraft,
  resultHeadline,
  suggestedLabel,
  taskKinds,
  withoutExtension,
  type ComponentDraft,
  type ComponentProposalResult,
  type ComponentSummary
} from "../lib/componentProposalContract";
import { canWithdraw, isRegistered, type OpenTask, type OwnProposal } from "../lib/ownProposalsContract";
import { parseShape } from "../lib/shape";

const CONCEPT_ID = "5f0e8c1a-7b2d-4e3f-9a10-222222222222";

const DRAFT: ComponentDraft = {
  ...emptyComponent(),
  label: "kutch-ajrakh/chemistry/indigo-vat",
  title: " Indigo vat ",
  description: " Shows indigo reduced to leuco-indigo in the vat and turning blue again in the air. ",
  kind: "reaction_player",
  field: "CHEMISTRY",
  craftSlug: "Kutch-Ajrakh",
  craftName: "Kutch Ajrakh",
  subjects: [{ kind: "CRAFT", key: " Kutch-Ajrakh " }, { kind: "CONCEPT", key: CONCEPT_ID }],
  consideredLabels: ["shared/chemistry/mordant-bath"]
};

const HELD: ComponentSummary = {
  label: "shared/chemistry/indigo-reduction",
  title: "Indigo reduction",
  description: "Indigo reduced in an alkaline vat.",
  kind: "reaction_player",
  field: "CHEMISTRY",
  fields: ["PROCESS"],
  craftSlug: null,
  subjects: [{ kind: "CONCEPT", key: CONCEPT_ID, name: "Indigo" }]
};

const TASK: OpenTask = {
  key: "MISSING_COMPONENT:craft:Kutch-Ajrakh:molecules",
  kind: "MISSING_COMPONENT",
  priority: "MEDIUM",
  subject: { kind: "craft", slug: "Kutch-Ajrakh", name: "Kutch Ajrakh", pageUrl: "https://kalavigyan.example/crafts/Kutch-Ajrakh" },
  field: null,
  need: "molecules",
  needed: "A 3D molecule for this craft",
  acceptance: "A registered molecule_3d component keyed to the craft",
  count: 0,
  factIds: [],
  sourceIds: [],
  prompt: "propose_component",
  reservedUntil: null
};

test("a component needs a registry label, a title, a description for the model, a kind, a field and a subject", () => {
  expect(componentProblems(emptyComponent())).toEqual([
    "Give a label of the form craft-or-shared/field/name, in lower case with hyphens.",
    "Give it a title.",
    "Describe it in at least 40 characters, for the model that will place it.",
    "Choose its kind.",
    "Choose its field.",
    "Key it to at least one craft, concept, compound or place."
  ]);
  expect(componentProblems(DRAFT)).toEqual([]);
  expect(componentProblems({ ...DRAFT, label: "Kutch-Ajrakh/chemistry/vat" })[0]).toMatch(/^Give a label/);
  expect(componentProblems({ ...DRAFT, label: "shared/vat" })[0]).toMatch(/^Give a label/);
});

test("subjects are named once, places by lgd or basin, and concepts or compounds by their id", () => {
  const subjects = [
    { kind: "CRAFT" as const, key: "Kutch-Ajrakh" },
    { kind: "CRAFT" as const, key: " Kutch-Ajrakh" },
    { kind: "PLACE" as const, key: "Kachchh" },
    { kind: "COMPOUND" as const, key: "indigo" },
    { kind: "CONCEPT" as const, key: " " }
  ];
  expect(componentProblems({ ...DRAFT, subjects })).toEqual([
    "Name each subject once.",
    "Give every subject its key.",
    "Key a place as lgd: and its district code, or basin: and its id.",
    "Key a concept or compound by its id."
  ]);
  expect(componentProblems({ ...DRAFT, subjects: [{ kind: "PLACE", key: "lgd:468" }, { kind: "PLACE", key: "basin:luni" }] })).toEqual([]);
});

test("the body trims the words and subject keys and leaves out the owning craft's name", () => {
  expect(componentBody(DRAFT)).toEqual({
    label: "kutch-ajrakh/chemistry/indigo-vat",
    title: "Indigo vat",
    description: "Shows indigo reduced to leuco-indigo in the vat and turning blue again in the air.",
    kind: "reaction_player",
    field: "CHEMISTRY",
    fields: [],
    craftSlug: "Kutch-Ajrakh",
    subjects: [{ kind: "CRAFT", key: "Kutch-Ajrakh" }, { kind: "CONCEPT", key: CONCEPT_ID }],
    consideredLabels: ["shared/chemistry/mordant-bath"],
    extends: null,
    extension: null,
    taskKey: null
  });
});

test("the suggested label is the owning craft or shared, the field and the title in lower case with hyphens", () => {
  expect(suggestedLabel("Kutch-Ajrakh", "CHEMISTRY", "Indigo vat: reduction!")).toBe("kutch-ajrakh/chemistry/indigo-vat-reduction");
  expect(suggestedLabel(null, "BOTANY", "  Madder root  ")).toBe("shared/botany/madder-root");
  expect(suggestedLabel(null, "", "Madder")).toBe("");
  expect(suggestedLabel(null, "BOTANY", "!!")).toBe("");
});

test("a subject link keeps the held label and a variant takes its own, both naming what they extend", () => {
  const link = extendedDraft(DRAFT, HELD, "SUBJECT_LINK");
  expect([link.label, link.extends, link.extension, link.kind, link.field, link.craftSlug]).toEqual([HELD.label, HELD.label, "SUBJECT_LINK", "reaction_player", "CHEMISTRY", null]);
  expect(componentProblems(link)).toEqual([]);
  const variant = extendedDraft(DRAFT, HELD, "VARIANT");
  expect([variant.label, variant.extends, variant.craftSlug]).toEqual([DRAFT.label, HELD.label, "Kutch-Ajrakh"]);
  expect(componentProblems({ ...variant, label: HELD.label })).toEqual(["A variant takes a label of its own."]);
  expect(componentProblems({ ...link, label: DRAFT.label })).toEqual(["A new subject link keeps the label of the component it extends."]);
  const fresh = extendedDraft({ ...emptyComponent(), subjects: [{ kind: "CRAFT", key: "Bagh-Print" }] }, HELD, "SUBJECT_LINK");
  expect([fresh.title, fresh.description]).toEqual([HELD.title, HELD.description]);
  expect(withoutExtension(link)).toMatchObject({ label: "", extends: null, extension: null });
  expect(withoutExtension(variant)).toMatchObject({ label: DRAFT.label, extends: null, extension: null });
});

test("every component shown by the search is recorded as considered, once each and at most fifty", () => {
  expect(consideredAfter(["shared/chemistry/mordant-bath"], [HELD, { ...HELD }])).toEqual(["shared/chemistry/mordant-bath", HELD.label]);
  const many = Array.from({ length: 60 }, (_, index) => ({ ...HELD, label: `shared/chemistry/piece-${index}` }));
  const considered = consideredAfter([], many);
  expect([considered.length, considered[49]]).toEqual([50, "shared/chemistry/piece-49"]);
});

test("an open task keys the component to its craft, offers only the kinds its need takes and names the task", () => {
  const needs = { molecules: ["molecule_3d"], pictures: ["images", "picture_plate", "specimen_plate"] };
  const kinds = ["images", "molecule_3d", "what_if"];
  expect(taskKinds(kinds, needs, TASK)).toEqual(["molecule_3d"]);
  expect(taskKinds(kinds, needs, null)).toEqual(kinds);
  const started = componentFromTask({ ...emptyComponent(), kind: "what_if", subjects: [{ kind: "CRAFT", key: "Kutch-Ajrakh" }, { kind: "PLACE", key: "lgd:468" }] }, TASK, ["molecule_3d"]);
  expect([started.craftSlug, started.craftName, started.kind, started.taskKey]).toEqual(["Kutch-Ajrakh", "Kutch Ajrakh", "molecule_3d", TASK.key]);
  expect(started.subjects).toEqual([{ kind: "CRAFT", key: "Kutch-Ajrakh" }, { kind: "PLACE", key: "lgd:468" }]);
  const family = { ...TASK, subject: { ...TASK.subject!, kind: "family" as const } };
  expect(componentFromTask(DRAFT, family, ["molecule_3d"])).toBe(DRAFT);
});

test("a refusal returns the close matches with their reasons, and a stored proposal says who decides", () => {
  const refused: ComponentProposalResult = {
    schemaVersion: 1,
    outcome: "REFUSED",
    proposalId: null,
    status: null,
    label: DRAFT.label,
    message: "The library already holds 1 component that shows this.",
    matches: [{ component: HELD, reasons: ["the same kind, keyed to the same concept"] }],
    waysOn: ["Place it.", "Extend it."]
  };
  expect(parseShape(componentResultShape, refused)).toEqual(refused);
  expect(() => parseShape(componentResultShape, { ...refused, matches: [{ component: HELD, reasons: [] }] })).toThrow();
  expect(resultHeadline(refused)).toBe("Not stored: the library already holds it");
  const stored = { ...refused, outcome: "STORED" as const, proposalId: "p", status: "PENDING" as const, matches: [], waysOn: [] };
  expect(resultHeadline(stored)).toBe("Received: it waits for an Admin's review");
  expect(resultHeadline({ ...stored, status: "APPROVED" })).toBe("Approved at once: it waits to be built");
});

const REGISTERED: OwnProposal = {
  id: "5f0e8c1a-7b2d-4e3f-9a10-333333333333",
  kind: "COMPONENT",
  state: "APPROVED",
  status: "APPROVED",
  text: "Plain timeline of the printers",
  description: "A plain timeline of the printers' years, registered earlier.",
  label: "sanganeri-hand-block-printing/history/plain-timeline",
  componentKind: "timeline",
  field: "HISTORY",
  subjectName: "Sanganeri Hand Block Printing",
  craftSlug: "Sanganeri-Hand-Block-Printing",
  createdAt: "2026-11-23T09:00:00Z",
  reasons: [],
  gates: [],
  registered: true
};

test("a registered component of yours is withdrawn or replaced, an approved one still being built is not", () => {
  expect([canWithdraw(REGISTERED), isRegistered(REGISTERED)]).toEqual([true, true]);
  const building = { ...REGISTERED, registered: false };
  expect([canWithdraw(building), isRegistered(building)]).toEqual([false, false]);
  const older = { ...REGISTERED, registered: undefined };
  expect(isRegistered(older)).toBe(false);
  expect(canWithdraw({ ...REGISTERED, state: "WAITING", status: "PENDING", registered: false })).toBe(true);
});

test("a replacement starts from the component it replaces and takes a label of its own", () => {
  const fresh = replacingDraft(emptyComponent(), REGISTERED);
  expect([fresh.replaces, fresh.label, fresh.kind, fresh.field, fresh.craftSlug, fresh.craftName]).toEqual([
    REGISTERED.label,
    "",
    "timeline",
    "HISTORY",
    "Sanganeri-Hand-Block-Printing",
    "Sanganeri Hand Block Printing"
  ]);
  expect(fresh.subjects).toEqual([{ kind: "CRAFT", key: "Sanganeri-Hand-Block-Printing" }]);
  expect([fresh.extends, fresh.extension]).toEqual([null, null]);
  const named = { ...fresh, label: "sanganeri-hand-block-printing/history/dated-timeline", title: "Printers' dated timeline", description: "The dated years of the printers' work, each year from a cited fact." };
  expect(componentProblems(named)).toEqual([]);
  expect(componentProblems({ ...named, label: REGISTERED.label! })).toEqual(["A replacement takes a label of its own."]);
  expect(componentBody(named).replaces).toBe(REGISTERED.label);
  expect("replaces" in componentBody(DRAFT)).toBe(false);
});
