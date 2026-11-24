"use client";

import { FieldChoice, KindChoice, Problems, SubjectCraft } from "@/components/contributions/ProposalFields";
import { SubjectFields } from "@/components/contributions/SubjectFields";
import { TermsConsent } from "@/components/contributions/TermsConsent";
import type { ComponentProposal } from "@/components/contributions/useComponentProposal";
import { Field, TextArea, TextInput } from "@/components/FormControls";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { DESCRIPTION_MAX, LABEL_MAX, suggestedLabel, TITLE_MAX, withoutExtension, type ComponentDraft } from "@/lib/componentProposalContract";
import type { ProposalForm } from "@/lib/ownProposalsContract";

export function ComponentForm({ proposal, form }: { proposal: ComponentProposal; form: ProposalForm }) {
  const { draft, busy } = proposal;
  const set = (patch: Partial<ComponentDraft>) => proposal.setDraft({ ...draft, ...patch });
  return (
    <form className="grid gap-6" noValidate onSubmit={(event) => { event.preventDefault(); void proposal.send(); }} data-testid="component-form">
      <h2 className="font-reading text-h3 text-ink-1">Describe the component</h2>
      <Extending draft={draft} disabled={busy} onStop={() => proposal.setDraft(withoutExtension(draft))} />
      <Replacing draft={draft} disabled={busy} onStop={() => set({ replaces: null })} />
      <Field label="Title">
        <TextInput value={draft.title} disabled={busy} maxLength={TITLE_MAX} onChange={(event) => set({ title: event.target.value })} />
      </Field>
      <Field label="What it shows and when to place it" hint={`Written for the model that places it. ${draft.description.trim().length} of ${DESCRIPTION_MAX} characters, at least 40.`}>
        <TextArea value={draft.description} disabled={busy} maxLength={DESCRIPTION_MAX} rows={4} onChange={(event) => set({ description: event.target.value })} />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <KindChoice kinds={proposal.kinds} value={draft.kind} disabled={busy || draft.extension !== null} onChange={(kind) => set({ kind })} />
        <FieldChoice fields={form.fields} value={draft.field} disabled={busy || draft.extension !== null} onChange={(field) => set({ field, fields: draft.fields.filter((each) => each !== field) })} />
      </div>
      <SubjectCraft
        label="Owning craft"
        kind="craft"
        slug={draft.craftSlug ?? ""}
        name={draft.craftName}
        hint="Leave it empty for a component every craft may share."
        disabled={busy}
        onChange={(slug, name) => set({ craftSlug: slug || null, craftName: name })}
      />
      <SubjectFields subjects={draft.subjects} disabled={busy} onChange={(subjects) => set({ subjects })} />
      <LabelField draft={draft} disabled={busy || draft.extension === "SUBJECT_LINK"} onChange={(label) => set({ label })} />
      <TermsConsent terms={form.terms} ticked={proposal.ticked} disabled={busy} onTick={proposal.setTicked} />
      <Problems problems={proposal.problems} />
      <ActionGroup align="start">
        <Button type="submit" variant="primary" busy={busy} busyLabel="Searching the library">
          Propose the component
        </Button>
      </ActionGroup>
    </form>
  );
}

function LabelField({ draft, disabled, onChange }: { draft: ComponentDraft; disabled: boolean; onChange: (label: string) => void }) {
  const suggested = suggestedLabel(draft.craftSlug, draft.field, draft.title);
  return (
    <div className="grid gap-2">
      <Field label="Label" hint="Its name in the registry: the owning craft or shared, the field, then a name, in lower case with hyphens.">
        <TextInput value={draft.label} className="font-code" disabled={disabled} maxLength={LABEL_MAX} onChange={(event) => onChange(event.target.value.trim())} placeholder={suggested || "shared/chemistry/indigo-reduction"} />
      </Field>
      {suggested && suggested !== draft.label && !disabled ? (
        <ActionGroup align="start">
          <Button type="button" variant="text" size="sm" onClick={() => onChange(suggested)}>
            Use {suggested}
          </Button>
        </ActionGroup>
      ) : null}
    </div>
  );
}

function Replacing({ draft, disabled, onStop }: { draft: ComponentDraft; disabled: boolean; onStop: () => void }) {
  if (!draft.replaces) return null;
  return (
    <div className="grid gap-2 border-s-2 border-ink-1 ps-4" data-testid="replacing">
      <p className="font-ui text-ui text-ink-1">
        Takes the place of <span className="font-code [overflow-wrap:anywhere]">{draft.replaces}</span> on every page once it is registered
      </p>
      <ActionGroup align="start">
        <Button type="button" variant="text" size="sm" disabled={disabled} onClick={onStop}>
          Propose it as a new component instead
        </Button>
      </ActionGroup>
    </div>
  );
}

function Extending({ draft, disabled, onStop }: { draft: ComponentDraft; disabled: boolean; onStop: () => void }) {
  if (!draft.extends) return null;
  const how = draft.extension === "SUBJECT_LINK" ? "Keys it to another subject" : "A variant";
  return (
    <div className="grid gap-2 border-s-2 border-ink-1 ps-4" data-testid="extending">
      <p className="font-ui text-ui text-ink-1">
        {how} of <span className="font-code [overflow-wrap:anywhere]">{draft.extends}</span>
      </p>
      <ActionGroup align="start">
        <Button type="button" variant="text" size="sm" disabled={disabled} onClick={onStop}>
          Make it a new component instead
        </Button>
      </ActionGroup>
    </div>
  );
}
