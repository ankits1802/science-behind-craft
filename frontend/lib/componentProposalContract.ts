import { apiFetch, buildQuery } from "@/lib/api";
import { DISCIPLINES, type Discipline } from "@/lib/explainerBlockBase";
import { PROPOSALS_PATH, type OpenTask } from "@/lib/ownProposalsContract";
import { list, nullable, object, oneOf, parseShape, text, type Shape } from "@/lib/shape";

export const COMPONENTS_PATH = `${PROPOSALS_PATH}/components`;
export const LIBRARY_PATH = `${PROPOSALS_PATH}/library`;
export const COMPONENT_SUBJECT_KINDS = ["CRAFT", "CONCEPT", "PLACE", "COMPOUND"] as const;
export const EXTENSIONS = ["SUBJECT_LINK", "VARIANT"] as const;
export const COMPONENT_OUTCOMES = ["STORED", "REFUSED"] as const;
export const COMPONENT_STATUSES = ["PENDING", "APPROVED", "REJECTED", "WITHDRAWN"] as const;
export const LABEL_PATTERN = /^[a-z0-9]+(-[a-z0-9]+)*(\/[a-z0-9]+(-[a-z0-9]+)*){2,}$/;
export const LABEL_MAX = 200;
export const TITLE_MIN = 3;
export const TITLE_MAX = 200;
export const DESCRIPTION_MIN = 40;
export const DESCRIPTION_MAX = 600;
export const SUBJECTS_MAX = 20;
export const CONSIDERED_MAX = 50;
export const SHARED_OWNER = "shared";

const PLACE_KEY = /^(lgd|basin):[A-Za-z0-9_-]+$/;
const ID_KEY = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export type ComponentSubjectKind = (typeof COMPONENT_SUBJECT_KINDS)[number];
export type Extension = (typeof EXTENSIONS)[number];
export type SubjectDraft = { kind: ComponentSubjectKind; key: string };
export type ComponentDraft = {
  label: string;
  title: string;
  description: string;
  kind: string;
  field: Discipline | "";
  fields: Discipline[];
  craftSlug: string | null;
  craftName: string;
  subjects: SubjectDraft[];
  consideredLabels: string[];
  extends: string | null;
  extension: Extension | null;
  taskKey: string | null;
};

export type ComponentSubject = { kind: ComponentSubjectKind; key: string; name: string };
export type ComponentSummary = {
  label: string;
  title: string;
  description: string;
  kind: string;
  field: Discipline;
  fields: Discipline[];
  craftSlug: string | null;
  subjects: ComponentSubject[];
};
export type CraftComponents = { schemaVersion: 1; craftSlug: string | null; field: Discipline | null; kind: string | null; query: string | null; components: ComponentSummary[] };
export type ComponentMatch = { component: ComponentSummary; reasons: string[] };
export type ComponentProposalResult = {
  schemaVersion: 1;
  outcome: (typeof COMPONENT_OUTCOMES)[number];
  proposalId: string | null;
  status: (typeof COMPONENT_STATUSES)[number] | null;
  label: string;
  message: string;
  matches: ComponentMatch[];
  waysOn: string[];
};
export type LibraryQuery = { query: string; craftSlug: string | null; kind: string | null };

const field = oneOf(DISCIPLINES);

export const componentSummaryShape: Shape<ComponentSummary> = object<ComponentSummary>({
  label: text,
  title: text,
  description: text,
  kind: text,
  field,
  fields: list(field),
  craftSlug: nullable(text),
  subjects: list(object<ComponentSubject>({ kind: oneOf(COMPONENT_SUBJECT_KINDS), key: text, name: text }))
});

const craftComponentsShape: Shape<CraftComponents> = object<CraftComponents>({
  schemaVersion: oneOf([1] as const),
  craftSlug: nullable(text),
  field: nullable(field),
  kind: nullable(text),
  query: nullable(text),
  components: list(componentSummaryShape)
});

export const componentResultShape: Shape<ComponentProposalResult> = object<ComponentProposalResult>({
  schemaVersion: oneOf([1] as const),
  outcome: oneOf(COMPONENT_OUTCOMES),
  proposalId: nullable(text),
  status: nullable(oneOf(COMPONENT_STATUSES)),
  label: text,
  message: text,
  matches: list(object<ComponentMatch>({ component: componentSummaryShape, reasons: list(text, 1) })),
  waysOn: list(text)
});

export function emptyComponent(): ComponentDraft {
  return { label: "", title: "", description: "", kind: "", field: "", fields: [], craftSlug: null, craftName: "", subjects: [], consideredLabels: [], extends: null, extension: null, taskKey: null };
}

export function suggestedLabel(craftSlug: string | null, field: Discipline | "", title: string): string {
  const name = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  if (!field || !name) return "";
  const owner = (craftSlug ?? SHARED_OWNER).toLowerCase();
  const head = `${owner}/${field.toLowerCase()}/`;
  return `${head}${name.slice(0, LABEL_MAX - head.length).replace(/-+$/, "")}`;
}

export function consideredAfter(considered: readonly string[], shown: readonly ComponentSummary[]): string[] {
  return [...new Set([...considered, ...shown.map((component) => component.label)])].slice(0, CONSIDERED_MAX);
}

export function extendedDraft(draft: ComponentDraft, component: ComponentSummary, extension: Extension): ComponentDraft {
  const link = extension === "SUBJECT_LINK";
  const ownLabel = draft.label === component.label ? "" : draft.label;
  return {
    ...draft,
    label: link ? component.label : ownLabel,
    title: draft.title || (link ? component.title : ""),
    description: draft.description || (link ? component.description : ""),
    kind: component.kind,
    field: component.field,
    fields: draft.fields.filter((each) => each !== component.field),
    craftSlug: link ? component.craftSlug : draft.craftSlug,
    craftName: link ? (component.craftSlug ?? "") : draft.craftName,
    extends: component.label,
    extension
  };
}

export function withoutExtension(draft: ComponentDraft): ComponentDraft {
  const label = draft.extension === "SUBJECT_LINK" ? "" : draft.label;
  return { ...draft, label, extends: null, extension: null };
}

export function taskKinds(kinds: readonly string[], needs: Record<string, string[]>, task: OpenTask | null): string[] {
  if (!task?.need) return [...kinds];
  const wanted = needs[task.need] ?? [];
  return kinds.filter((kind) => wanted.includes(kind));
}

export function componentFromTask(draft: ComponentDraft, task: OpenTask, kinds: readonly string[]): ComponentDraft {
  if (task.subject?.kind !== "craft") return draft;
  const slug = task.subject.slug;
  const subjects: SubjectDraft[] = [{ kind: "CRAFT", key: slug }, ...draft.subjects.filter((each) => !(each.kind === "CRAFT" && each.key === slug))];
  const kind = kinds.includes(draft.kind) ? draft.kind : (kinds[0] ?? "");
  return { ...draft, craftSlug: slug, craftName: task.subject.name, kind, field: task.field ?? draft.field, subjects: subjects.slice(0, SUBJECTS_MAX), taskKey: task.key };
}

export function componentProblems(draft: ComponentDraft): string[] {
  const problems: string[] = [];
  if (!LABEL_PATTERN.test(draft.label) || draft.label.length > LABEL_MAX) problems.push("Give a label of the form craft-or-shared/field/name, in lower case with hyphens.");
  if (draft.title.trim().length < TITLE_MIN) problems.push("Give it a title.");
  if (draft.title.trim().length > TITLE_MAX) problems.push(`Keep the title to ${TITLE_MAX} characters.`);
  const description = draft.description.trim().length;
  if (description < DESCRIPTION_MIN) problems.push(`Describe it in at least ${DESCRIPTION_MIN} characters, for the model that will place it.`);
  if (description > DESCRIPTION_MAX) problems.push(`Keep the description to ${DESCRIPTION_MAX} characters.`);
  if (!draft.kind) problems.push("Choose its kind.");
  if (!draft.field) problems.push("Choose its field.");
  problems.push(...subjectProblems(draft.subjects));
  if (draft.extension === "SUBJECT_LINK" && draft.label !== draft.extends) problems.push("A new subject link keeps the label of the component it extends.");
  if (draft.extension === "VARIANT" && draft.label === draft.extends) problems.push("A variant takes a label of its own.");
  return problems;
}

function subjectProblems(subjects: readonly SubjectDraft[]): string[] {
  const problems: string[] = [];
  if (!subjects.length) problems.push("Key it to at least one craft, concept, compound or place.");
  if (subjects.length > SUBJECTS_MAX) problems.push(`Key it to at most ${SUBJECTS_MAX} subjects.`);
  const keys = subjects.map((subject) => `${subject.kind}:${subject.key.trim()}`);
  if (new Set(keys).size !== keys.length) problems.push("Name each subject once.");
  if (subjects.some((subject) => !subject.key.trim())) problems.push("Give every subject its key.");
  if (subjects.some((subject) => subject.kind === "PLACE" && subject.key.trim() && !PLACE_KEY.test(subject.key.trim()))) {
    problems.push("Key a place as lgd: and its district code, or basin: and its id.");
  }
  if (subjects.some((subject) => (subject.kind === "CONCEPT" || subject.kind === "COMPOUND") && subject.key.trim() && !ID_KEY.test(subject.key.trim()))) {
    problems.push("Key a concept or compound by its id.");
  }
  return problems;
}

export function componentBody(draft: ComponentDraft): Record<string, unknown> {
  return {
    label: draft.label,
    title: draft.title.trim(),
    description: draft.description.trim(),
    kind: draft.kind,
    field: draft.field,
    fields: draft.fields,
    craftSlug: draft.craftSlug,
    subjects: draft.subjects.map((subject) => ({ kind: subject.kind, key: subject.key.trim() })),
    consideredLabels: draft.consideredLabels,
    extends: draft.extends,
    extension: draft.extension,
    taskKey: draft.taskKey
  };
}

export function resultHeadline(result: ComponentProposalResult): string {
  if (result.outcome === "REFUSED") return "Not stored: the library already holds it";
  return result.status === "APPROVED" ? "Approved at once: it waits to be built" : "Received: it waits for an Admin's review";
}

export async function searchLibrary(search: LibraryQuery): Promise<CraftComponents> {
  const query = buildQuery({ query: search.query.trim() || undefined, craftSlug: search.craftSlug, kind: search.kind });
  return parseShape(craftComponentsShape, await apiFetch<unknown>(`${LIBRARY_PATH}${query}`));
}

export async function proposeComponent(draft: ComponentDraft): Promise<ComponentProposalResult> {
  const body = await apiFetch<unknown>(COMPONENTS_PATH, { method: "POST", body: JSON.stringify(componentBody(draft)) });
  return parseShape(componentResultShape, body);
}
