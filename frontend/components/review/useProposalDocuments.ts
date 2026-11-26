"use client";

import { useCallback, useState } from "react";

import { apiErrorMessage } from "@/lib/api";
import type { MonographDocument } from "@/lib/monographDocument";
import { fetchProposalDocument, type DrawnSide } from "@/lib/pageProposalContract";

const READ_FAILED = "Couldn't read the page's drawing just now. Try again.";

export type ProposalDocuments = {
  documents: Partial<Record<DrawnSide, MonographDocument>>;
  busy: boolean;
  problem: string | null;
  load: (sides: readonly DrawnSide[]) => Promise<void>;
};

export function useProposalDocuments(id: string): ProposalDocuments {
  const [documents, setDocuments] = useState<Partial<Record<DrawnSide, MonographDocument>>>({});
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const load = useCallback(
    async (sides: readonly DrawnSide[]) => {
      const wanted = sides.filter((side) => !documents[side]);
      if (!wanted.length) return;
      setBusy(true);
      setProblem(null);
      try {
        const read = await Promise.all(wanted.map(async (side) => [side, await fetchProposalDocument(id, side)] as const));
        setDocuments((current) => ({ ...current, ...Object.fromEntries(read) }));
      } catch (cause) {
        setProblem(apiErrorMessage(cause, READ_FAILED));
      } finally {
        setBusy(false);
      }
    },
    [documents, id]
  );

  return { documents, busy, problem, load };
}
