"use client";

import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from "react";

import { useAuth } from "@/components/AuthProvider";
import { ApiError, apiErrorMessage } from "@/lib/api";
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
import { decisionBody, LINK_NOT_ADMIN, linkRefusal, linkToRead, withLinked, withProposal } from "@/lib/pageProposalView";
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
  linkNote: string | null;
  handlers: PageProposalHandlers;
};

function useLinkedProposal(focused: string | null, listed: PageProposalView[] | null, setProposals: Dispatch<SetStateAction<PageProposalView[]>>): string | null {
  const [refused, setRefused] = useState<{ id: string; note: string } | null>(null);
  const wanted = linkToRead(focused, listed);
  useEffect(() => {
    if (wanted === null) return;
    let cancelled = false;
    fetchPageProposal(wanted).then(
      (found) => {
        if (!cancelled) setProposals((current) => withLinked(current, found));
      },
      (cause: unknown) => {
        if (!cancelled) setRefused({ id: wanted, note: linkRefusal(cause instanceof ApiError ? cause.status : null) });
      }
    );
    return () => {
      cancelled = true;
    };
  }, [wanted, setProposals]);
  return refused !== null && refused.id === focused ? refused.note : null;
}

export function usePageProposals(onDecided: () => void, focused: string | null = null): PageProposals {
  const { user } = useAuth();
  const allowed = hasRank(user, "ADMIN");
  const [proposals, setProposals] = useState<PageProposalView[]>([]);
  const [listed, setListed] = useState<PageProposalView[] | null>(null);
  const [opened, setOpened] = useState<Record<string, PageProposalView>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const linkNote = useLinkedProposal(allowed ? focused : null, listed, setProposals);

  useEffect(() => {
    if (!allowed) return;
    let cancelled = false;
    fetchPageProposals()
      .then((found) => {
        if (cancelled) return;
        setProposals(found.proposals);
        setListed(found.proposals);
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

  const note = allowed ? linkNote : focused !== null && user !== null ? LINK_NOT_ADMIN : null;
  return { proposals: allowed ? proposals : [], opened, error: allowed ? error : null, notice, linkNote: note, handlers: { open, decide, draw } };
}

async function attempt(work: () => Promise<void>, fallback: string): Promise<string | null> {
  try {
    await work();
    return null;
  } catch (cause) {
    return apiErrorMessage(cause, fallback);
  }
}
