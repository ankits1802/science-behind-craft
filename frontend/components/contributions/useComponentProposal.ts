"use client";

import { useState } from "react";

import type { Contributions } from "@/components/contributions/useContributions";
import { apiErrorMessage } from "@/lib/api";
import {
  componentFromTask,
  componentProblems,
  consideredAfter,
  emptyComponent,
  extendedDraft,
  proposeComponent,
  taskKinds,
  type ComponentDraft,
  type ComponentProposalResult,
  type ComponentSummary,
  type Extension
} from "@/lib/componentProposalContract";
import { termsAccepted, withTerms, type OpenTask } from "@/lib/ownProposalsContract";

const SEND_FAILED = "Couldn't send the component. Nothing was stored; try again.";

export type ComponentProposal = {
  draft: ComponentDraft;
  kinds: string[];
  describing: boolean;
  ticked: boolean;
  busy: boolean;
  problems: string[];
  result: ComponentProposalResult | null;
  setDraft: (next: ComponentDraft) => void;
  setTicked: (ticked: boolean) => void;
  startFrom: (task: OpenTask) => void;
  describe: (shown: readonly ComponentSummary[]) => void;
  extend: (component: ComponentSummary, extension: Extension, shown: readonly ComponentSummary[]) => void;
  send: () => Promise<void>;
};

export function useComponentProposal(contributions: Contributions): ComponentProposal {
  const [draft, setDraft] = useState<ComponentDraft>(emptyComponent);
  const [task, setTask] = useState<OpenTask | null>(null);
  const [describing, setDescribing] = useState(false);
  const [ticked, setTicked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [problems, setProblems] = useState<string[]>([]);
  const [result, setResult] = useState<ComponentProposalResult | null>(null);
  const form = contributions.form;
  const kinds = taskKinds(form?.kinds ?? [], form?.needs ?? {}, task);

  function startFrom(chosen: OpenTask) {
    setTask(chosen);
    setDraft((current) => componentFromTask(current, chosen, taskKinds(form?.kinds ?? [], form?.needs ?? {}, chosen)));
    setResult(null);
  }

  function describe(shown: readonly ComponentSummary[]) {
    setDraft((current) => ({ ...current, consideredLabels: consideredAfter(current.consideredLabels, shown) }));
    setDescribing(true);
  }

  function extend(component: ComponentSummary, extension: Extension, shown: readonly ComponentSummary[]) {
    setDraft((current) => extendedDraft({ ...current, consideredLabels: consideredAfter(current.consideredLabels, shown) }, component, extension));
    setDescribing(true);
    setResult(null);
  }

  async function send() {
    const terms = form?.terms ?? null;
    const found = withTerms(componentProblems(draft), terms, ticked);
    setProblems(found);
    if (found.length || !terms) return;
    setBusy(true);
    setResult(null);
    try {
      contributions.setTerms(await termsAccepted(terms));
      const answer = await proposeComponent(draft);
      setResult(answer);
      settle(answer);
      await contributions.reload();
    } catch (cause) {
      setProblems([apiErrorMessage(cause, SEND_FAILED)]);
    } finally {
      setBusy(false);
    }
  }

  function settle(answer: ComponentProposalResult) {
    if (answer.outcome === "REFUSED") {
      setDraft((current) => ({ ...current, consideredLabels: consideredAfter(current.consideredLabels, answer.matches.map((match) => match.component)) }));
      return;
    }
    setDraft(emptyComponent());
    setTask(null);
    setDescribing(false);
  }

  return { draft, kinds, describing, ticked, busy, problems, result, setDraft, setTicked, startFrom, describe, extend, send };
}
