"use client";

import { BookPlus } from "lucide-react";

import { FactForm } from "@/components/contributions/FactForm";
import { FactReply } from "@/components/contributions/FactReply";
import { MyContributions } from "@/components/contributions/MyContributions";
import { OpenWorkStarts } from "@/components/contributions/OpenWorkStarts";
import { FormPending } from "@/components/contributions/ProposalFields";
import { useContributions } from "@/components/contributions/useContributions";
import { useFactProposal } from "@/components/contributions/useFactProposal";
import { PageHeader } from "@/components/PageHeader";
import { TextLink } from "@/components/ui/TextLink";
import { FACT_TASK_KINDS, FACT_TASK_SUBJECTS, itemsOfKind } from "@/lib/ownProposalsContract";

export default function ProposeFactPage() {
  const contributions = useContributions();
  const proposal = useFactProposal(contributions);
  const { form, items, error, notice, busy } = contributions;
  return (
    <>
      <PageHeader
        title="Propose a fact"
        description="One fact about a craft, in one sentence, with the words of the sources that state it. Every source is read and checked before anything is shown."
        icon={<BookPlus className="h-5 w-5" aria-hidden />}
      />
      <div className="grid gap-12">
        <p className="font-ui text-ui text-ink-2">
          A 3D molecule, a what-if or a map instead? <TextLink href="/contributions/components">Propose a component</TextLink>
        </p>
        <OpenWorkStarts kinds={FACT_TASK_KINDS} subjects={FACT_TASK_SUBJECTS} disabled={proposal.busy} onPick={proposal.startFrom} />
        {form ? <FactForm proposal={proposal} form={form} /> : <FormPending failed={Boolean(error)} />}
        <FactReply reply={proposal.reply} />
        {notice ? <p role="status" className="font-ui text-ui text-ink-1">{notice}</p> : null}
        {error ? <p role="alert" className="font-ui text-ui text-error">{error}</p> : null}
        <section className="grid gap-4" aria-labelledby="my-facts-h">
          <h2 id="my-facts-h" className="font-reading text-h3 text-ink-1">Your facts</h2>
          <MyContributions
            items={items ? itemsOfKind(items, "FACT") : null}
            form={form}
            busy={busy}
            empty="Facts you propose appear here with what the checks and the reviewers said. Withdraw one while it waits for review."
            onWithdraw={(item) => void contributions.withdraw(item)}
          />
        </section>
      </div>
    </>
  );
}
