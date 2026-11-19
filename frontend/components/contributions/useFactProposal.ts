"use client";

import { useState } from "react";

import type { Contributions } from "@/components/contributions/useContributions";
import { apiErrorMessage } from "@/lib/api";
import { emptyFact, factFromTask, factProblems, proposeFact, type FactDraft, type ProposalReply } from "@/lib/factProposalContract";
import { termsAccepted, withTerms, type OpenTask } from "@/lib/ownProposalsContract";

const SEND_FAILED = "Couldn't send the fact. Nothing was stored; try again.";

export type FactProposal = {
  draft: FactDraft;
  ticked: boolean;
  busy: boolean;
  problems: string[];
  reply: ProposalReply | null;
  setDraft: (next: FactDraft) => void;
  setTicked: (ticked: boolean) => void;
  startFrom: (task: OpenTask) => void;
  send: () => Promise<void>;
};

export function useFactProposal(contributions: Contributions): FactProposal {
  const [draft, setDraft] = useState<FactDraft>(emptyFact);
  const [ticked, setTicked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [problems, setProblems] = useState<string[]>([]);
  const [reply, setReply] = useState<ProposalReply | null>(null);
  const terms = contributions.form?.terms ?? null;

  async function send() {
    const found = withTerms(factProblems(draft), terms, ticked);
    setProblems(found);
    if (found.length || !terms) return;
    setBusy(true);
    setReply(null);
    try {
      contributions.setTerms(await termsAccepted(terms));
      const answer = await proposeFact(draft);
      setReply(answer);
      if (answer.outcome !== "REFUSED") setDraft(emptyFact());
      await contributions.reload();
    } catch (cause) {
      setProblems([apiErrorMessage(cause, SEND_FAILED)]);
    } finally {
      setBusy(false);
    }
  }

  function startFrom(task: OpenTask) {
    setDraft((current) => factFromTask(current, task));
    setReply(null);
  }

  return { draft, ticked, busy, problems, reply, setDraft, setTicked, startFrom, send };
}
