import type { ReactNode } from "react";

import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import type { ComponentSummary, Extension } from "@/lib/componentProposalContract";
import { kindLabel } from "@/lib/ownProposalsContract";

type CardProps = {
  component: ComponentSummary;
  fieldTitle: string;
  reasons?: string[];
  children?: ReactNode;
};

export function ComponentCard({ component, fieldTitle, reasons, children }: CardProps) {
  const subjects = component.subjects.map((subject) => subject.name).join(", ");
  return (
    <li className="grid gap-2 border-t border-rule pt-4" data-testid="library-component">
      <p className="kicker">{[kindLabel(component.kind), fieldTitle].filter(Boolean).join(" · ")}</p>
      <h3 className="font-reading text-h3 text-ink-1">{component.title}</h3>
      <p className="font-code text-label text-ink-2 [overflow-wrap:anywhere]">{component.label}</p>
      <p className="max-w-measure font-reading text-body-sm text-ink-1">{component.description}</p>
      {subjects ? <p className="font-ui text-label text-ink-3">Keyed to {subjects}</p> : null}
      {reasons?.length ? (
        <ul className="grid max-w-measure gap-1 font-ui text-label text-ink-2" aria-label="Why it is close">
          {reasons.map((reason) => (
            <li key={reason}>Close: {reason}</li>
          ))}
        </ul>
      ) : null}
      {children}
    </li>
  );
}

export function ExtendActions({ disabled, onExtend }: { disabled: boolean; onExtend: (extension: Extension) => void }) {
  return (
    <ActionGroup align="start">
      <Button type="button" variant="quiet" size="sm" disabled={disabled} onClick={() => onExtend("SUBJECT_LINK")}>
        Key it to another subject
      </Button>
      <Button type="button" variant="quiet" size="sm" disabled={disabled} onClick={() => onExtend("VARIANT")}>
        Propose a variant
      </Button>
    </ActionGroup>
  );
}
