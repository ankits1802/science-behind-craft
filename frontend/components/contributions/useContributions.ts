"use client";

import { useCallback, useEffect, useState } from "react";

import { apiErrorMessage } from "@/lib/api";
import {
  fetchMyProposals,
  fetchProposalForm,
  withdrawProposal,
  type OwnProposal,
  type ProposalForm,
  type TermsStatus
} from "@/lib/ownProposalsContract";

const FORM_FAILED = "Couldn't read the fields and the contribution terms. Reload the page.";
const LIST_FAILED = "Couldn't read your contributions. Reload the page.";
const WITHDRAW_FAILED = "Couldn't withdraw it. Reload the page and try again.";
const WITHDRAWN = "Withdrawn. It will not be shown.";

export type Contributions = {
  form: ProposalForm | null;
  items: OwnProposal[] | null;
  error: string | null;
  busy: boolean;
  notice: string | null;
  reload: () => Promise<void>;
  withdraw: (item: OwnProposal) => Promise<void>;
  setTerms: (terms: TermsStatus) => void;
};

function useProposalForm(onError: (message: string) => void) {
  const [form, setForm] = useState<ProposalForm | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetchProposalForm()
      .then((found) => {
        if (!cancelled) setForm(found);
      })
      .catch((cause) => {
        if (!cancelled) onError(apiErrorMessage(cause, FORM_FAILED));
      });
    return () => {
      cancelled = true;
    };
  }, [onError]);
  const setTerms = useCallback((terms: TermsStatus) => setForm((current) => (current ? { ...current, terms } : current)), []);
  return { form, setTerms };
}

export function useContributions(): Contributions {
  const [items, setItems] = useState<OwnProposal[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const { form, setTerms } = useProposalForm(setError);

  const reload = useCallback(async () => {
    try {
      setItems(await fetchMyProposals());
    } catch (cause) {
      setError(apiErrorMessage(cause, LIST_FAILED));
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const withdraw = useCallback(
    async (item: OwnProposal) => {
      setBusy(true);
      setNotice(null);
      try {
        await withdrawProposal(item);
        setNotice(WITHDRAWN);
        await reload();
      } catch (cause) {
        setError(apiErrorMessage(cause, WITHDRAW_FAILED));
      } finally {
        setBusy(false);
      }
    },
    [reload]
  );

  return { form, items, error, busy, notice, reload, withdraw, setTerms };
}
