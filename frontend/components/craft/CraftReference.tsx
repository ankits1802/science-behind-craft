"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { CitationProvider } from "@/components/answer/CitationContext";
import { ExplainerReadingProvider } from "@/components/answer/ExplainerReading";
import { SourceDialog } from "@/components/answer/SourceDialog";
import { TermSheet } from "@/components/answer/TermSheet";
import { useAuth } from "@/components/AuthProvider";
import { CraftClaimsProvider } from "@/components/craft/CraftClaims";
import { CraftEvidence } from "@/components/craft/CraftEvidence";
import { CraftOverview } from "@/components/craft/CraftOverview";
import { CraftRegionTab } from "@/components/craft/CraftRegionTab";
import { CraftSharedScience } from "@/components/craft/CraftSharedScience";
import { CraftSourcesTab } from "@/components/craft/CraftSourcesTab";
import { CraftTabs, craftPanelId, craftTabId } from "@/components/craft/CraftTabs";
import { CraftVoice, type CraftVoiceProps } from "@/components/craft/CraftVoice";
import { ProcessTimeline } from "@/components/craft/ProcessTimeline";
import { useCraftReading } from "@/components/craft/useCraftReading";
import { useRemote } from "@/components/hooks/useRemote";
import { useRevealRow } from "@/components/hooks/useRevealRow";
import type { CraftPage } from "@/lib/craftPageContract";
import { craftTabs, shownTab, sourceGroups, type CraftTab } from "@/lib/craftPageView";
import { fetchCraftRegion } from "@/lib/craftRegion";
import { fetchCraftSharedScience } from "@/lib/learningApi";
import { canReadAllEvidence } from "@/lib/permissions";
import type { SourceRef } from "@/lib/types";

export type ReferenceVoice = Pick<CraftVoiceProps, "open" | "onClose" | "availability">;

const NO_SOURCES: SourceRef[] = [];

function useStageReveal(tab: CraftTab, onTab: (tab: CraftTab) => void) {
  const { registerRow, reveal, flashKey } = useRevealRow();
  const [pending, setPending] = useState<{ stageId: string; nonce: number } | null>(null);
  const openStage = useCallback(
    (stageId: string) => {
      onTab("process");
      setPending((previous) => ({ stageId, nonce: (previous?.nonce ?? 0) + 1 }));
    },
    [onTab]
  );
  useEffect(() => {
    if (!pending || tab !== "process") return;
    reveal(pending.stageId);
    setPending(null);
  }, [pending, reveal, tab]);
  return { rows: { register: registerRow, flashKey }, openStage };
}

export function CraftReference({ page, requested, onTab, voice }: { page: CraftPage; requested: string | null; onTab: (tab: CraftTab) => void; voice: ReferenceVoice | null }) {
  const slug = page.craft.slug;
  const region = useRemote(useCallback(() => fetchCraftRegion(slug), [slug]));
  const regionSources = region.data?.sources ?? NO_SOURCES;
  const science = useRemote(useCallback(() => fetchCraftSharedScience(slug), [slug])).data;
  const shared = science !== null && science.nodes.length > 0;
  const reading = useCraftReading(page, regionSources);
  const evidence = canReadAllEvidence(useAuth().user);
  const tabs = useMemo(
    () => craftTabs(page, { sources: page.sources.length + regionSources.length > 0, evidence, science: shared }),
    [evidence, page, regionSources.length, shared]
  );
  const tab = shownTab(requested, tabs);
  const stages = useStageReveal(tab, onTab);

  return (
    <CraftClaimsProvider value={reading.index}>
      <ExplainerReadingProvider value={reading.reading}>
        <CitationProvider value={reading.lookup}>
          <CraftTabs tabs={tabs} value={tab} onChange={onTab} />
          <section id={craftPanelId(tab)} role="tabpanel" aria-labelledby={craftTabId(tab)} tabIndex={0} className="mt-4 focus-visible:outline-offset-4" data-testid={`craft-panel-${tab}`}>
            {tab === "overview" ? <CraftOverview page={page} /> : null}
            {tab === "process" ? <ProcessTimeline process={page.process} pictures={page.pictures} rows={stages.rows} /> : null}
            {tab === "region" ? <CraftRegionTab page={page} region={region} /> : null}
            {tab === "science" && science ? <CraftSharedScience science={science} numbered={reading.numbers} /> : null}
            {tab === "sources" ? <CraftSourcesTab groups={sourceGroups(reading.sourcesById.values(), reading.numbers)} numbers={reading.numbers} /> : null}
            {tab === "evidence" && page.evidence ? <CraftEvidence evidence={page.evidence} /> : null}
          </section>
          <SourceDialog open={reading.opened} onClose={reading.closeSource} />
          <TermSheet
            span={reading.terms.span}
            language={reading.reading.language.code}
            onClose={reading.terms.close}
            onMissing={reading.terms.missing}
            onAsk={null}
            onOpenCitation={reading.openSource}
          />
          {voice ? <CraftVoice {...voice} craftSlug={slug} process={page.process} onTab={onTab} onStage={stages.openStage} /> : null}
        </CitationProvider>
      </ExplainerReadingProvider>
    </CraftClaimsProvider>
  );
}
