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
  replacingDraft,
  taskKinds,
  type ComponentDraft,
  type ComponentProposalResult,
  type ComponentSummary,
  type Extension
} from "@/lib/componentProposalContract";
import { termsAccepted, withTerms, type OpenTask, type OwnProposal, type ProposalForm } from "@/lib/ownProposalsContract";

const SEND_FAILED = "Couldn't send the component. Nothing was stored; try again.";

type Shown = readonly ComponentSummary[];

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
  describe: (shown: Shown) => void;
  extend: (component: ComponentSummary, extension: Extension, shown: Shown) => void;
  replace: (item: OwnProposal) => void;
  send: () => Promise<void>;
};

function useComponentDraft(form: ProposalForm | null) {
  const [draft, setDraft] = useState<ComponentDraft>(emptyComponent);
  const [task, setTask] = useState<OpenTask | null>(null);
  const [describing, setDescribing] = useState(false);
  const kindsFor = (chosen: OpenTask | null) => taskKinds(form?.kinds ?? [], form?.needs ?? {}, chosen);
  const consider = (shown: Shown) => setDraft((current) => ({ ...current, consideredLabels: consideredAfter(current.consideredLabels, shown) }));
  return {
    draft,
    describing,
    setDraft,
    consider,
    kinds: kindsFor(task),
    startFrom: (chosen: OpenTask) => {
      setTask(chosen);
      setDraft((current) => componentFromTask(current, chosen, kindsFor(chosen)));
    },
    describe: (shown: Shown) => {
      consider(shown);
      setDescribing(true);
    },
    extend: (component: ComponentSummary, extension: Extension, shown: Shown) => {
      setDraft((current) => extendedDraft({ ...current, consideredLabels: consideredAfter(current.consideredLabels, shown) }, component, extension));
      setDescribing(true);
    },
    replace: (item: OwnProposal) => {
      setDraft((current) => replacingDraft(current, item));
      setDescribing(true);
    },
    reset: () => {
      setDraft(emptyComponent());
      setTask(null);
      setDescribing(false);
    }
  };
}

export function useComponentProposal(contributions: Contributions): ComponentProposal {
  const editing = useComponentDraft(contributions.form);
  const [ticked, setTicked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [problems, setProblems] = useState<string[]>([]);
  const [result, setResult] = useState<ComponentProposalResult | null>(null);

  async function send() {
    const terms = contributions.form?.terms ?? null;
    const found = withTerms(componentProblems(editing.draft), terms, ticked);
    setProblems(found);
    if (found.length || !terms) return;
    setBusy(true);
    setResult(null);
    try {
      contributions.setTerms(await termsAccepted(terms));
      const answer = await proposeComponent(editing.draft);
      setResult(answer);
      if (answer.outcome === "REFUSED") editing.consider(answer.matches.map((match) => match.component));
      else editing.reset();
      await contributions.reload();
    } catch (cause) {
      setProblems([apiErrorMessage(cause, SEND_FAILED)]);
    } finally {
      setBusy(false);
    }
  }

  const { draft, kinds, describing, setDraft, describe } = editing;
  const startFrom = (task: OpenTask) => {
    editing.startFrom(task);
    setResult(null);
  };
  const extend = (component: ComponentSummary, extension: Extension, shown: Shown) => {
    editing.extend(component, extension, shown);
    setResult(null);
  };
  const replace = (item: OwnProposal) => {
    editing.replace(item);
    setResult(null);
  };
  return { draft, kinds, describing, ticked, busy, problems, result, setDraft, setTicked, startFrom, describe, extend, replace, send };
}
