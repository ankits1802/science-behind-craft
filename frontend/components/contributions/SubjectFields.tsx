"use client";

import { FieldBlock, Select, TextInput } from "@/components/FormControls";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { COMPONENT_SUBJECT_KINDS, SUBJECTS_MAX, type ComponentSubjectKind, type SubjectDraft } from "@/lib/componentProposalContract";
import { removed, replaced } from "@/lib/ownProposalsContract";

const SUBJECT_LABELS: Record<ComponentSubjectKind, string> = {
  CRAFT: "A craft, by its slug",
  CONCEPT: "A concept, by its id",
  COMPOUND: "A compound, by its id",
  PLACE: "A place, as lgd: or basin: and its code"
};

type SubjectsProps = { subjects: SubjectDraft[]; disabled: boolean; onChange: (next: SubjectDraft[]) => void };

export function SubjectFields({ subjects, disabled, onChange }: SubjectsProps) {
  return (
    <FieldBlock label="Keyed to" hint={<span className="kv-field-hint">The crafts, concepts, compounds or places it shows. A page offers it when it is keyed to the page&apos;s subject.</span>}>
      <ul className="grid gap-3">
        {subjects.map((subject, index) => (
          <li key={index} className="grid gap-2 sm:grid-cols-[minmax(0,16rem)_minmax(0,1fr)_auto] sm:items-center">
            <Select value={subject.kind} aria-label={`Subject ${index + 1}: what it is`} disabled={disabled} onChange={(event) => onChange(replaced(subjects, index, { ...subject, kind: event.target.value as ComponentSubjectKind }))}>
              {COMPONENT_SUBJECT_KINDS.map((kind) => (
                <option key={kind} value={kind}>
                  {SUBJECT_LABELS[kind]}
                </option>
              ))}
            </Select>
            <TextInput value={subject.key} aria-label={`Subject ${index + 1}: its key`} maxLength={64} disabled={disabled} onChange={(event) => onChange(replaced(subjects, index, { ...subject, key: event.target.value }))} />
            <ActionGroup align="start" inline>
              <Button type="button" variant="text" size="sm" disabled={disabled} onClick={() => onChange(removed(subjects, index))}>
                Remove subject {index + 1}
              </Button>
            </ActionGroup>
          </li>
        ))}
      </ul>
      {subjects.length < SUBJECTS_MAX ? (
        <ActionGroup align="start" className="mt-3">
          <Button type="button" variant="quiet" size="sm" disabled={disabled} onClick={() => onChange([...subjects, { kind: "CRAFT", key: "" }])}>
            Add a subject
          </Button>
        </ActionGroup>
      ) : null}
    </FieldBlock>
  );
}
