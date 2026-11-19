"use client";

import { FieldChoice, Problems, SubjectCraft } from "@/components/contributions/ProposalFields";
import { SourceFields } from "@/components/contributions/SourceFields";
import { TermsConsent } from "@/components/contributions/TermsConsent";
import type { FactProposal } from "@/components/contributions/useFactProposal";
import { Field, TextArea } from "@/components/FormControls";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { canAddSource, emptySource, STATEMENT_MAX, type FactDraft } from "@/lib/factProposalContract";
import { removed, replaced, type ProposalForm } from "@/lib/ownProposalsContract";

export function FactForm({ proposal, form }: { proposal: FactProposal; form: ProposalForm }) {
  const { draft, busy } = proposal;
  const set = (patch: Partial<FactDraft>) => proposal.setDraft({ ...draft, ...patch });
  return (
    <form className="grid gap-6" noValidate onSubmit={(event) => { event.preventDefault(); void proposal.send(); }} data-testid="fact-form">
      <FactSubject draft={draft} disabled={busy} onChange={set} />
      <FieldChoice fields={form.fields} value={draft.field} disabled={busy} onChange={(field) => set({ field, fields: draft.fields.filter((each) => each !== field) })} />
      <Field label="The fact" hint={`One fact in one sentence. ${draft.statement.trim().length} of ${STATEMENT_MAX} characters.`}>
        <TextArea value={draft.statement} disabled={busy} maxLength={STATEMENT_MAX} rows={3} onChange={(event) => set({ statement: event.target.value })} />
      </Field>
      {draft.sources.map((source, index) => (
        <SourceFields
          key={index}
          source={source}
          number={index + 1}
          disabled={busy}
          onChange={(next) => set({ sources: replaced(draft.sources, index, next) })}
          onRemove={draft.sources.length > 1 ? () => set({ sources: removed(draft.sources, index) }) : null}
        />
      ))}
      {canAddSource(draft) ? (
        <ActionGroup align="start">
          <Button type="button" variant="quiet" size="sm" disabled={busy} onClick={() => set({ sources: [...draft.sources, emptySource()] })}>
            Add another source
          </Button>
        </ActionGroup>
      ) : null}
      <TermsConsent terms={form.terms} ticked={proposal.ticked} disabled={busy} onTick={proposal.setTicked} />
      <Problems problems={proposal.problems} />
      <ActionGroup align="start">
        <Button type="submit" variant="primary" busy={busy} busyLabel="Checking the sources">
          Send the fact
        </Button>
      </ActionGroup>
    </form>
  );
}

function FactSubject({ draft, disabled, onChange }: { draft: FactDraft; disabled: boolean; onChange: (patch: Partial<FactDraft>) => void }) {
  return (
    <SubjectCraft
      label={draft.subjectKind === "category" ? "Category" : "Craft"}
      kind={draft.subjectKind}
      slug={draft.subjectSlug}
      name={draft.subjectName}
      disabled={disabled}
      onChange={(slug, name) => onChange({ subjectKind: "craft", subjectSlug: slug, subjectName: name })}
    />
  );
}
