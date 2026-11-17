"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import { BookOpen } from "lucide-react";

import { SourceDialog, type OpenCitation } from "@/components/answer/SourceDialog";
import { CitationProvider, type CitationLookup } from "@/components/answer/CitationContext";
import { ClaimList, NoSourceFound } from "@/components/craft/ClaimList";
import { CraftHeader } from "@/components/craft/CraftHeader";
import { CraftRegionTab } from "@/components/craft/CraftRegionTab";
import { CraftSourcesTab } from "@/components/craft/CraftSourcesTab";
import { CraftTabs, craftPanelId, craftTabId } from "@/components/craft/CraftTabs";
import { CraftVoice, type CraftVoiceProps } from "@/components/craft/CraftVoice";
import { ProcessTimeline } from "@/components/craft/ProcessTimeline";
import { useStageMedia } from "@/components/craft/useStageMedia";
import { failureMessage, useRemote, type RemoteFailure } from "@/components/hooks/useRemote";
import { useRevealRow } from "@/components/hooks/useRevealRow";
import { PageHeader } from "@/components/PageHeader";
import { RemoteView } from "@/components/RemotePanels";
import { useVoiceAvailability, useVoiceOffered } from "@/components/voice/useVoiceOffer";
import { ApiError } from "@/lib/api";
import { craftSources, fetchCraftProcess, fetchCraftProfile, fetchCraftRegion, isCraftTab, type CraftTab } from "@/lib/craftProfile";
import { recordLoadFailure } from "@/lib/recordView";
import type { Citation, CraftProfile } from "@/lib/types";

function profileFailure(failure: RemoteFailure): string {
  const cause = failure.cause;
  return cause instanceof ApiError ? recordLoadFailure("craft", cause.status, cause.message) : recordLoadFailure("craft", null);
}

export default function CraftPage() {
  return (
    <Suspense fallback={null}>
      <CraftScreen />
    </Suspense>
  );
}

function CraftScreen() {
  const { slug } = useParams<{ slug: string }>();
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const profile = useRemote(useCallback(() => fetchCraftProfile(slug), [slug]));
  const availability = useVoiceAvailability();
  const voiceOffered = useVoiceOffered(availability);
  const [voiceOpen, setVoiceOpen] = useState(false);
  const requested = params.get("tab");
  const tab: CraftTab = isCraftTab(requested) ? requested : "overview";

  const setTab = (next: CraftTab) => {
    const search = new URLSearchParams(params.toString());
    if (next === "overview") search.delete("tab");
    else search.set("tab", next);
    const query = search.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  if (!profile.data) {
    return (
      <>
        <PageHeader title="Craft" icon={<BookOpen className="h-5 w-5" aria-hidden />} />
        <RemoteView remote={profile} failed={profileFailure}>
          {() => null}
        </RemoteView>
      </>
    );
  }

  return (
    <>
      <CraftHeader craft={profile.data.craft} onVoice={voiceOffered ? () => setVoiceOpen(true) : undefined} />
      <CraftTabs value={tab} onChange={setTab} />
      <CraftPanels
        slug={slug}
        profile={profile.data}
        tab={tab}
        onTab={setTab}
        voice={voiceOffered ? { open: voiceOpen, onClose: () => setVoiceOpen(false), availability } : null}
      />
    </>
  );
}

type PanelVoice = Pick<CraftVoiceProps, "open" | "onClose" | "availability">;

function CraftPanels({ slug, profile, tab, onTab, voice }: { slug: string; profile: CraftProfile; tab: CraftTab; onTab: (tab: CraftTab) => void; voice: PanelVoice | null }) {
  const process = useRemote(useCallback(() => fetchCraftProcess(slug), [slug]));
  const region = useRemote(useCallback(() => fetchCraftRegion(slug), [slug]));
  const stageMedia = useStageMedia(profile.craft.slug);
  const [open, setOpen] = useState<OpenCitation | null>(null);
  const { registerRow, reveal, flashKey } = useRevealRow();
  const [pendingStage, setPendingStage] = useState<{ stageId: string; nonce: number } | null>(null);
  const openStage = useCallback(
    (stageId: string) => {
      onTab("process");
      setPendingStage((previous) => ({ stageId, nonce: (previous?.nonce ?? 0) + 1 }));
    },
    [onTab]
  );

  useEffect(() => {
    if (!pendingStage || tab !== "process" || !process.data) return;
    reveal(pendingStage.stageId);
    setPendingStage(null);
  }, [pendingStage, process.data, reveal, tab]);
  const sources = useMemo(() => craftSources(profile, process.data, region.data), [profile, process.data, region.data]);
  const onOpen = useCallback(
    (citation: Citation) => setOpen({ citation, source: sources.byId.get(citation.sourceId) ?? null, number: sources.numbers.get(citation.sourceId) ?? null }),
    [sources]
  );
  const lookup: CitationLookup = useMemo(() => ({ numbers: sources.numbers, sourcesById: sources.byId, onOpen }), [onOpen, sources]);

  return (
    <CitationProvider value={lookup}>
      <section id={craftPanelId(tab)} role="tabpanel" aria-labelledby={craftTabId(tab)} tabIndex={0} className="mt-4 focus-visible:outline-offset-4" data-testid={`craft-panel-${tab}`}>
        {tab === "overview" ? (
          <div className="panel p-5 md:p-6">
            {profile.craft.description ? <p className="mb-4 text-[15px] leading-7 text-ink-700">{profile.craft.description}</p> : null}
            <ClaimList claims={profile.overview} />
          </div>
        ) : null}
        {tab === "region" ? <CraftRegionTab profile={profile} region={region} /> : null}
        {tab === "process" ? (
          <RemoteView remote={process} failed={(failure) => failureMessage(failure, "Couldn't load the process.")}>
            {(data) => <ProcessTimeline process={data} rows={{ register: registerRow, flashKey }} stageMedia={stageMedia} />}
          </RemoteView>
        ) : null}
        {tab === "materials" ? <MaterialsPanel materials={profile.materials} /> : null}
        {tab === "sources" ? <CraftSourcesTab sources={sources.ordered} numbers={sources.numbers} /> : null}
      </section>
      <SourceDialog open={open} onClose={() => setOpen(null)} />
      {voice ? <CraftVoice {...voice} craftSlug={profile.craft.slug} process={process.data} onTab={onTab} onStage={openStage} /> : null}
    </CitationProvider>
  );
}

function MaterialsPanel({ materials }: { materials: CraftProfile["materials"] }) {
  if (materials.length === 0) {
    return (
      <div className="panel p-5">
        <NoSourceFound />
      </div>
    );
  }
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {materials.map((material) => (
        <section key={material.id} className="panel p-5">
          <h3 className="font-display text-base font-bold text-ink-900">{material.name}</h3>
          {material.description ? <p className="mt-1 text-sm text-ink-500">{material.description}</p> : null}
          <div className="mt-3">
            <ClaimList claims={material.claims} />
          </div>
        </section>
      ))}
    </div>
  );
}
