"use client";

import { Field, TextArea, TextInput } from "@/components/FormControls";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import {
  canAddQuote,
  emptyQuote,
  LICENCE_MAX,
  LOCATOR_MAX,
  QUOTE_MAX,
  SOURCE_TITLE_MAX,
  type QuoteDraft,
  type SourceDraft
} from "@/lib/factProposalContract";
import { removed, replaced } from "@/lib/ownProposalsContract";

type SourceProps = {
  source: SourceDraft;
  number: number;
  disabled: boolean;
  onChange: (next: SourceDraft) => void;
  onRemove: (() => void) | null;
};

export function SourceFields({ source, number, disabled, onChange, onRemove }: SourceProps) {
  const set = (patch: Partial<SourceDraft>) => onChange({ ...source, ...patch });
  return (
    <fieldset className="grid gap-4 border-t border-rule pt-4" data-testid="fact-source">
      <legend className="font-ui text-h4 text-ink-1">Source {number}</legend>
      <Field label="Address" hint="The https address of the page that states the fact.">
        <TextInput type="url" inputMode="url" value={source.url} disabled={disabled} onChange={(event) => set({ url: event.target.value })} placeholder="https://" />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Title">
          <TextInput value={source.title} disabled={disabled} maxLength={SOURCE_TITLE_MAX} onChange={(event) => set({ title: event.target.value })} />
        </Field>
        <Field label="Licence" hint="Optional, as the source states it, for example CC BY 4.0.">
          <TextInput value={source.licence} disabled={disabled} maxLength={LICENCE_MAX} onChange={(event) => set({ licence: event.target.value })} />
        </Field>
      </div>
      {source.quotes.map((quote, index) => (
        <QuoteFields
          key={index}
          quote={quote}
          number={index + 1}
          disabled={disabled}
          onChange={(next) => set({ quotes: replaced(source.quotes, index, next) })}
          onRemove={source.quotes.length > 1 ? () => set({ quotes: removed(source.quotes, index) }) : null}
        />
      ))}
      <SourceActions number={number} disabled={disabled} onAddQuote={canAddQuote(source) ? () => set({ quotes: [...source.quotes, emptyQuote()] }) : null} onRemove={onRemove} />
    </fieldset>
  );
}

type ActionsProps = { number: number; disabled: boolean; onAddQuote: (() => void) | null; onRemove: (() => void) | null };

function SourceActions({ number, disabled, onAddQuote, onRemove }: ActionsProps) {
  return (
    <ActionGroup align="start">
      {onAddQuote ? (
        <Button type="button" variant="quiet" size="sm" disabled={disabled} onClick={onAddQuote}>
          Add a quote
        </Button>
      ) : null}
      {onRemove ? (
        <Button type="button" variant="danger" size="sm" disabled={disabled} onClick={onRemove} data-danger="">
          Remove source {number}
        </Button>
      ) : null}
    </ActionGroup>
  );
}

type QuoteProps = {
  quote: QuoteDraft;
  number: number;
  disabled: boolean;
  onChange: (next: QuoteDraft) => void;
  onRemove: (() => void) | null;
};

function QuoteFields({ quote, number, disabled, onChange, onRemove }: QuoteProps) {
  return (
    <div className="grid gap-3 border-s-2 border-rule ps-4" data-testid="fact-quote">
      <Field label={`Quote ${number}`} hint={`Copied exactly from the source, 20 to ${QUOTE_MAX} characters.`}>
        <TextArea value={quote.text} disabled={disabled} maxLength={QUOTE_MAX} rows={3} onChange={(event) => onChange({ ...quote, text: event.target.value })} />
      </Field>
      <Field label="Where it is" hint="Optional: a page, section or paragraph.">
        <TextInput value={quote.locator} disabled={disabled} maxLength={LOCATOR_MAX} onChange={(event) => onChange({ ...quote, locator: event.target.value })} />
      </Field>
      {onRemove ? (
        <ActionGroup align="start">
          <Button type="button" variant="text" size="sm" disabled={disabled} onClick={onRemove}>
            Remove quote {number}
          </Button>
        </ActionGroup>
      ) : null}
    </div>
  );
}
