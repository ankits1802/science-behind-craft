"use client";

import { GateResults } from "@/components/contributions/GateResults";
import { useConfirm } from "@/components/dialogs/ConfirmDialog";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/format";
import { canWithdraw, fieldTitle, kindLabel, stateLabel, type OwnProposal, type ProposalForm } from "@/lib/ownProposalsContract";

type ListProps = {
  items: OwnProposal[] | null;
  form: ProposalForm | null;
  busy: boolean;
  empty: string;
  onWithdraw: (item: OwnProposal) => void;
};

export function MyContributions({ items, form, busy, empty, onWithdraw }: ListProps) {
  const confirm = useConfirm();
  if (!items) {
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
      body: "It leaves the review queue and is not shown. To offer it again, propose it again.",
      confirmLabel: "Withdraw",
      tone: "danger"
    });
    if (sure) onWithdraw(item);
  }

  return (
    <ul className="grid gap-4" data-testid="my-contributions">
      {items.map((item) => (
        <ContributionRow key={item.id} item={item} form={form} busy={busy} onWithdraw={(chosen) => void withdraw(chosen)} />
      ))}
    </ul>
  );
}

function ContributionRow({ item, form, busy, onWithdraw }: { item: OwnProposal; form: ProposalForm | null; busy: boolean; onWithdraw: (item: OwnProposal) => void }) {
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
      {canWithdraw(item) ? (
        <ActionGroup align="start" inline>
          <Button type="button" variant="danger" size="sm" disabled={busy} onClick={() => onWithdraw(item)}>
            Withdraw
          </Button>
        </ActionGroup>
      ) : null}
    </li>
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
