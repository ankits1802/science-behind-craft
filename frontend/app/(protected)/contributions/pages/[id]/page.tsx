"use client";

import { useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { HeldPage } from "@/components/contributions/HeldPage";
import { failureMessage, useRemote } from "@/components/hooks/useRemote";
import { PageHeader } from "@/components/PageHeader";
import { LoadingPanel, RetryPanel } from "@/components/RemotePanels";
import { fetchHeldPage, type PageHoldView } from "@/lib/pageHoldContract";

const DESCRIPTION = "An app connected to your account proposed this page in your name. Nothing in it is proposed or shown to readers until you confirm it here.";

export default function ConfirmPagePage() {
  const { id } = useParams<{ id: string }>();
  const load = useMemo(() => () => fetchHeldPage(id), [id]);
  const held = useRemote(load);
  const [decided, setDecided] = useState<PageHoldView | null>(null);
  const view = decided ?? held.data;

  return (
    <>
      <PageHeader title="Confirm a page" description={DESCRIPTION} />
      {held.failure && !decided ? (
        <RetryPanel message={failureMessage(held.failure, "Couldn't open the page that waits for you.")} onRetry={held.retry} />
      ) : view ? (
        <HeldPage view={view} onDecided={setDecided} />
      ) : (
        <LoadingPanel label="Opening the page that waits for you" />
      )}
    </>
  );
}
