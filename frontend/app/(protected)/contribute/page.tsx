"use client";

import { useCallback, useEffect, useState } from "react";
import { Mic } from "lucide-react";

import { ConversationRun } from "@/components/artisan/ConversationRun";
import { ConversationSetup } from "@/components/artisan/ConversationSetup";
import { MyContributions } from "@/components/artisan/MyContributions";
import { PageHeader } from "@/components/PageHeader";
import { fetchAskConfig } from "@/lib/askConfig";
import { availabilityShape, type ConversationAvailability, type RelayConversationStarted } from "@/lib/conversationContract";
import { fetchProfile } from "@/lib/profileContract";
import { parseShape } from "@/lib/shape";
import { fetchContributions, type ContributionList } from "@/lib/testimonyContract";

export default function ContributePage() {
  const [offered, setOffered] = useState<ConversationAvailability | null>(null);
  const [spoken, setSpoken] = useState<string | null>(null);
  const [listed, setListed] = useState<ContributionList | null>(null);
  const [started, setStarted] = useState<RelayConversationStarted | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(() => {
    fetchAskConfig()
      .then((raw) => setOffered(parseShape(availabilityShape, (raw as { conversation?: unknown }).conversation)))
      .catch(() => setOffered(null));
    fetchProfile()
      .then((view) => setSpoken(view.artisan?.spokenLanguage ?? null))
      .catch(() => setSpoken(null));
    fetchContributions()
      .then(setListed)
      .catch(() => setFailed(true));
  }, []);

  useEffect(load, [load]);

  return (
    <>
      <PageHeader title="Your craft in your words" icon={<Mic className="h-5 w-5" aria-hidden />} back={false} />
      <div className="grid gap-6">
        {offered && offered.configured && offered.transport === "RELAY" ? (
          <section className="panel grid gap-4 p-5" data-testid="talk">
            {started ? (
              <ConversationRun started={started} onEnded={() => { setStarted(null); load(); }} />
            ) : (
              <ConversationSetup offered={offered} spoken={spoken} onAgreed={load} onStarted={setStarted} />
            )}
          </section>
        ) : null}
        {failed ? <p className="text-sm text-error-600">Couldn&apos;t load what you shared. Reload the page.</p> : null}
        {listed ? <MyContributions listed={listed} onChanged={load} /> : null}
      </div>
    </>
  );
}
