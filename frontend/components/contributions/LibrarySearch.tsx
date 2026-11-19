"use client";

import { ComponentCard, ExtendActions } from "@/components/contributions/ComponentCard";
import { KindChoice, SubjectCraft } from "@/components/contributions/ProposalFields";
import type { ComponentProposal } from "@/components/contributions/useComponentProposal";
import type { LibrarySearchState } from "@/components/contributions/useLibrarySearch";
import { Field, TextInput } from "@/components/FormControls";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { fieldTitle, type ProposalForm } from "@/lib/ownProposalsContract";

type SearchProps = { library: LibrarySearchState; form: ProposalForm; proposal: ComponentProposal };

export function LibrarySearch({ library, form, proposal }: SearchProps) {
  return (
    <section className="grid gap-6" aria-labelledby="library-h" data-testid="library-search">
      <div className="grid gap-1">
        <h2 id="library-h" className="font-reading text-h3 text-ink-1">First, search the library</h2>
        <p className="max-w-measure font-reading text-body-sm text-ink-2">A component the library holds is placed by its label, or extended; it is never copied.</p>
      </div>
      <form className="grid gap-4" onSubmit={(event) => { event.preventDefault(); void library.search(); }}>
        <Field label="What it shows">
          <TextInput value={library.query} maxLength={300} onChange={(event) => library.setQuery(event.target.value)} placeholder="For example, indigo reduction in the vat" />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <SubjectCraft
            label="Craft"
            kind="craft"
            slug={library.craft?.slug ?? ""}
            name={library.craft?.name ?? ""}
            hint="Optional: its components and the shared ones."
            disabled={library.searching}
            onChange={(slug, name) => library.setCraft(slug ? { slug, name } : null)}
          />
          <KindChoice kinds={form.kinds} value={library.kind} anyLabel="Any kind" disabled={library.searching} onChange={library.setKind} />
        </div>
        <ActionGroup align="start">
          <Button type="submit" variant={proposal.describing ? "quiet" : "primary"} busy={library.searching} busyLabel="Searching">
            Search the library
          </Button>
        </ActionGroup>
      </form>
      {library.error ? <p role="alert" className="font-ui text-ui text-error">{library.error}</p> : null}
      <Found library={library} form={form} proposal={proposal} />
    </section>
  );
}

function Found({ library, form, proposal }: SearchProps) {
  const found = library.found;
  if (!found) return null;
  return (
    <div className="grid gap-4">
      <p role="status" className="font-ui text-ui text-ink-2">
        {found.length ? `The library holds ${found.length === 1 ? "one component" : `${found.length} components`} like it.` : "The library holds nothing like it."}
      </p>
      {found.length ? (
        <ul className="grid gap-4">
          {found.map((component) => (
            <ComponentCard key={component.label} component={component} fieldTitle={fieldTitle(form, component.field)}>
              <ExtendActions disabled={proposal.busy} onExtend={(extension) => proposal.extend(component, extension, found)} />
            </ComponentCard>
          ))}
        </ul>
      ) : null}
      {proposal.describing ? null : (
        <ActionGroup align="start">
          <Button type="button" variant="quiet" onClick={() => proposal.describe(found)}>
            {found.length ? "None of these: describe a new one" : "Describe a new one"}
          </Button>
        </ActionGroup>
      )}
    </div>
  );
}
