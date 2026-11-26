"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { apiErrorMessage } from "@/lib/api";
import {
  decidePageProposal,
  drawProposalSide,
  fetchPageProposal,
  fetchPageProposals,
  type DrawnSide,
  type PageAction,
  type PageProposalView,
  type PageScope
} from "@/lib/pageProposalContract";
import { decisionBody, withProposal } from "@/lib/pageProposalView";
import { hasRank } from "@/lib/permissions";

const LOAD_FAILED = "Couldn't read the page proposals. Reload the page to try again.";
const OPEN_FAILED = "Couldn't open this page proposal. Try again.";
const DECIDE_FAILED = "Couldn't save the decision. Open the proposal again and try once more.";
const DRAW_FAILED = "Couldn't draw it just now. Try again in a minute.";

export type PageProposalHandlers = {
  open: (id: string) => Promise<string | null>;
  decide: (id: string, scope: PageScope, action: PageAction, words: string) => Promise<string | null>;
  draw: (id: string, side: DrawnSide) => Promise<string | null>;
};

export type PageProposals = {
  proposals: PageProposalView[];
  opened: Record<string, PageProposalView>;
  error: string | null;
  notice: string | null;
  handlers: PageProposalHandlers;
};

export function usePageProposals(onDecided: () => void): PageProposals {
  const { user } = useAuth();
  const allowed = hasRank(user, "ADMIN");
  const [proposals, setProposals] = useState<PageProposalView[]>([]);
  const [opened, setOpened] = useState<Record<string, PageProposalView>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!allowed) return;
    let cancelled = false;
    fetchPageProposals()
      .then((found) => {
        if (!cancelled) setProposals(found.proposals);
      })
      .catch((cause: unknown) => {
        if (!cancelled) setError(apiErrorMessage(cause, LOAD_FAILED));
      });
    return () => {
      cancelled = true;
    };
  }, [allowed]);

  const reread = useCallback(async (id: string) => {
    const found = await fetchPageProposal(id);
    setOpened((current) => ({ ...current, [id]: found }));
    setProposals((current) => withProposal(current, found));
  }, []);

  const open = useCallback((id: string) => attempt(() => reread(id), OPEN_FAILED), [reread]);

  const decide = useCallback(
    (id: string, scope: PageScope, action: PageAction, words: string) =>
      attempt(async () => {
        const decided = await decidePageProposal(id, decisionBody(scope, action, words));
        setNotice(decided.message);
        await reread(id);
        onDecided();
      }, DECIDE_FAILED),
    [onDecided, reread]
  );

  const draw = useCallback(
    (id: string, side: DrawnSide) =>
      attempt(async () => {
        const drawing = await drawProposalSide(id, side);
        setNotice(drawing.message);
        await reread(id);
      }, DRAW_FAILED),
    [reread]
  );

  return { proposals: allowed ? proposals : [], opened, error: allowed ? error : null, notice, handlers: { open, decide, draw } };
}

async function attempt(work: () => Promise<void>, fallback: string): Promise<string | null> {
  try {
    await work();
    return null;
  } catch (cause) {
    return apiErrorMessage(cause, fallback);
  }
}
