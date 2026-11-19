"use client";

import { Field, FieldBlock, Select } from "@/components/FormControls";
import { CraftPicker } from "@/components/onboarding/CraftPicker";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import type { Discipline } from "@/lib/explainerBlockBase";
import { kindLabel, type FieldInfo } from "@/lib/ownProposalsContract";

type FieldChoiceProps = {
  fields: FieldInfo[];
  value: Discipline | "";
  disabled: boolean;
  onChange: (field: Discipline) => void;
};

export function FieldChoice({ fields, value, disabled, onChange }: FieldChoiceProps) {
  const chosen = fields.find((each) => each.field === value);
  return (
    <Field label="Field" hint={chosen ? `Covers ${chosen.covers}.` : "The part of the craft's page it belongs to."}>
      <Select value={value} placeholder="Choose a field" disabled={disabled} searchable onChange={(event) => onChange(event.target.value as Discipline)}>
        {fields.map((each) => (
          <option key={each.field} value={each.field}>
            {each.title}
          </option>
        ))}
      </Select>
    </Field>
  );
}

type KindChoiceProps = {
  kinds: string[];
  value: string;
  anyLabel?: string;
  disabled: boolean;
  onChange: (kind: string) => void;
};

export function KindChoice({ kinds, value, anyLabel, disabled, onChange }: KindChoiceProps) {
  return (
    <Field label="Kind" hint="What the reader sees: a 3D molecule, a what-if, a map, a reaction player, pictures and more.">
      <Select value={value} placeholder="Choose its kind" disabled={disabled} searchable onChange={(event) => onChange(event.target.value)}>
        {anyLabel ? <option value="">{anyLabel}</option> : null}
        {kinds.map((kind) => (
          <option key={kind} value={kind}>
            {kindLabel(kind)}
          </option>
        ))}
      </Select>
    </Field>
  );
}

type SubjectCraftProps = {
  label: string;
  kind: "craft" | "category";
  slug: string;
  name: string;
  hint?: string;
  disabled: boolean;
  onChange: (slug: string, name: string) => void;
};

export function SubjectCraft({ label, kind, slug, name, hint, disabled, onChange }: SubjectCraftProps) {
  if (kind === "category") {
    return (
      <FieldBlock label={label} hint={<span className="kv-field-hint">From the open work: a fact about the whole category.</span>}>
        <div className="flex flex-wrap items-center gap-3">
          <p className="font-reading text-body-sm text-ink-1">{name}</p>
          <ActionGroup align="start" inline>
            <Button type="button" variant="text" size="sm" disabled={disabled} onClick={() => onChange("", "")}>
              Choose a craft instead
            </Button>
          </ActionGroup>
        </div>
      </FieldBlock>
    );
  }
  const picked = slug ? [{ slug, displayName: name || slug }] : [];
  return (
    <Field label={label} hint={hint}>
      <CraftPicker picked={picked} onChange={(next) => onChange(next.at(-1)?.slug ?? "", next.at(-1)?.displayName ?? "")} />
    </Field>
  );
}

export function FormPending({ failed }: { failed: boolean }) {
  if (failed) return null;
  return (
    <p role="status" className="font-ui text-ui text-ink-3">
      Reading the fields and the contribution terms
    </p>
  );
}

export function Problems({ problems }: { problems: string[] }) {
  if (!problems.length) return null;
  return (
    <ul role="alert" className="grid gap-1 font-ui text-ui text-error" data-testid="proposal-problems">
      {problems.map((problem) => (
        <li key={problem}>{problem}</li>
      ))}
    </ul>
  );
}
