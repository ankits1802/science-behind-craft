"use client";

import { useId } from "react";

import { GateResults } from "@/components/contributions/GateResults";
import type { Contributions } from "@/components/contributions/useContributions";
import { useConfirm } from "@/components/dialogs/ConfirmDialog";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/format";
import { canWithdraw, fieldTitle, isRegistered, itemsOfKind, kindLabel, stateLabel, type OwnProposal, type ProposalForm, type ProposalKind } from "@/lib/ownProposalsContract";

const WAITING_BODY = "It leaves the review queue and is not shown. To offer it again, propose it again.";
const REGISTERED_BODY = "It comes off every page that places it and is kept in the record. To show a better one, replace it instead.";

type SectionProps = { title: string; kind: ProposalKind; empty: string; contributions: Contributions; onReplace?: (item: OwnProposal) => void };

export function ContributionsSection({ title, kind, empty, contributions, onReplace }: SectionProps) {
  const headingId = useId();
  const { items, form, busy, error } = contributions;
  return (
    <section className="grid gap-4" aria-labelledby={headingId}>
      <h2 id={headingId} className="font-reading text-h3 text-ink-1">{title}</h2>
      <MyContributions
        items={items ? itemsOfKind(items, kind) : null}
        failed={Boolean(error)}
        form={form}
        busy={busy}
        empty={empty}
        onWithdraw={(item) => void contributions.withdraw(item)}
        onReplace={onReplace}
      />
    </section>
  );
}

type ListProps = {
  items: OwnProposal[] | null;
  failed: boolean;
  form: ProposalForm | null;
  busy: boolean;
  empty: string;
  onWithdraw: (item: OwnProposal) => void;
  onReplace?: (item: OwnProposal) => void;
};

export function MyContributions({ items, failed, form, busy, empty, onWithdraw, onReplace }: ListProps) {
  const confirm = useConfirm();
  if (!items) {
    if (failed) return null;
    return (
      <p role="status" className="font-ui text-ui text-ink-3">
        Reading your contributions
      </p>
    );
  }
  if (!items.length) return <p className="max-w-measure font-reading text-body-sm text-ink-2">{empty}</p>;

  async function withdraw(item: OwnProposal) {
    const sure = await confirm({
      title: "Withdraw it?",
      body: isRegistered(item) ? REGISTERED_BODY : WAITING_BODY,
      confirmLabel: "Withdraw",
      tone: "danger"
    });
    if (sure) onWithdraw(item);
  }

  return (
    <ul className="grid gap-4" data-testid="my-contributions">
      {items.map((item) => (
        <ContributionRow key={item.id} item={item} form={form} busy={busy} onWithdraw={(chosen) => void withdraw(chosen)} onReplace={onReplace} />
      ))}
    </ul>
  );
}

type RowProps = { item: OwnProposal; form: ProposalForm | null; busy: boolean; onWithdraw: (item: OwnProposal) => void; onReplace?: (item: OwnProposal) => void };

function ContributionRow({ item, form, busy, onWithdraw, onReplace }: RowProps) {
  const about = [item.subjectName ?? "Shared", fieldTitle(form, item.field), item.componentKind ? kindLabel(item.componentKind) : ""].filter(Boolean);
  return (
    <li className="grid gap-2 border-t border-rule pt-4" data-state={item.state}>
      <p className="kicker">{about.join(" · ")}</p>
      <p className="max-w-measure font-reading text-body-sm text-ink-1">{item.text}</p>
      {item.label ? <p className="font-code text-label text-ink-2 [overflow-wrap:anywhere]">{item.label}</p> : null}
      <p className="font-ui text-label text-ink-2">
        {stateLabel(item)} · <span className="tabular-nums lining-nums">{formatDate(item.createdAt)}</span>
      </p>
      {item.state === "REFUSED" ? <GateResults gates={item.gates} /> : <Reasons reasons={item.reasons} />}
      <RowActions item={item} busy={busy} onWithdraw={onWithdraw} onReplace={onReplace} />
    </li>
  );
}

function RowActions({ item, busy, onWithdraw, onReplace }: Omit<RowProps, "form">) {
  const replaces = Boolean(onReplace) && isRegistered(item);
  if (!canWithdraw(item) && !replaces) return null;
  return (
    <ActionGroup align="start" inline>
      {replaces ? (
        <Button type="button" variant="quiet" size="sm" disabled={busy} onClick={() => onReplace?.(item)}>
          Replace
        </Button>
      ) : null}
      {canWithdraw(item) ? (
        <Button type="button" variant="danger" size="sm" data-danger disabled={busy} onClick={() => onWithdraw(item)}>
          Withdraw
        </Button>
      ) : null}
    </ActionGroup>
  );
}

function Reasons({ reasons }: { reasons: string[] }) {
  if (!reasons.length) return null;
  return (
    <ul className="grid max-w-measure gap-1 font-ui text-label text-ink-2" aria-label="The reviewer's reason">
      {reasons.map((reason) => (
        <li key={reason}>{reason}</li>
      ))}
    </ul>
  );
}
