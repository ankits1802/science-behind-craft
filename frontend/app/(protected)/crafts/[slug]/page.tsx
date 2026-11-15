"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { BookOpen, ExternalLink, FlaskConical, MessageCircleQuestion, RotateCw } from "lucide-react";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { CitationChip } from "@/components/answer/CitationChip";
import { EvidenceLevelBadge } from "@/components/answer/EvidenceBadge";
import { SourceDialog, type OpenCitation } from "@/components/answer/SourceDialog";
import { ClaimList, NoSourceFound } from "@/components/craft/ClaimList";
import { CraftTabs, craftPanelId, craftTabId } from "@/components/craft/CraftTabs";
import { riseItem, staggerParent } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { IndiaMapStage } from "@/components/map/IndiaMapStage";
import type { MapPoint } from "@/components/map/layout";
import { PageHeader } from "@/components/PageHeader";
import { ApiError } from "@/lib/api";
import { sourceByline, sourceHost, sourceHref, uniqueCitations } from "@/lib/citations";
import { fetchCraftProfile, isCraftTab, locationCaption, profileSourceNumbers, type CraftTab } from "@/lib/craftProfile";
import { recordLoadFailure } from "@/lib/recordView";
import type { Citation, CraftProfile, SourceRef } from "@/lib/types";

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
  const reduce = useAppReducedMotion();
  const [profile, setProfile] = useState<CraftProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [round, setRound] = useState(0);
  const [open, setOpen] = useState<OpenCitation | null>(null);
  const requested = params.get("tab");
  const tab: CraftTab = isCraftTab(requested) ? requested : "overview";

  useEffect(() => {
    let cancelled = false;
    setError(null);
    fetchCraftProfile(slug)
      .then((next) => {
        if (!cancelled) setProfile(next);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(recordLoadFailure("craft", err instanceof ApiError ? err.status : null, err instanceof Error ? err.message : null));
      });
    return () => {
      cancelled = true;
    };
  }, [round, slug]);

  const sourcesById = useMemo(() => new Map((profile?.sources ?? []).map((source) => [source.id, source])), [profile]);
  const numbers = useMemo(() => (profile ? profileSourceNumbers(profile) : new Map<string, number>()), [profile]);
  const onOpen = useCallback(
    (citation: Citation) => setOpen({ citation, source: sourcesById.get(citation.sourceId) ?? null, number: numbers.get(citation.sourceId) ?? null }),
    [numbers, sourcesById]
  );

  const setTab = (next: CraftTab) => {
    const search = new URLSearchParams(params.toString());
    if (next === "overview") search.delete("tab");
    else search.set("tab", next);
    const query = search.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  if (!profile) {
    return (
      <>
        <PageHeader title="Craft" icon={<BookOpen className="h-5 w-5" aria-hidden />} />
        {error ? (
          <section role="alert" className="panel grid justify-items-center gap-3 p-6 text-center">
            <p className="text-sm text-ink-700">{error}</p>
            <button type="button" className="field-button" onClick={() => setRound((value) => value + 1)}>
              <RotateCw className="h-4 w-4" aria-hidden />
              Try again
            </button>
          </section>
        ) : (
          <section className="panel p-6 text-sm text-ink-500">Loading…</section>
        )}
      </>
    );
  }

  const { craft } = profile;
  const path = [craft.categoryName, craft.subCategoryName].filter(Boolean).join(" › ");

  return (
    <>
      <PageHeader
        title={craft.name}
        description={[craft.localName && craft.localName !== craft.name ? craft.localName : null, path].filter(Boolean).join(" · ") || undefined}
        icon={<BookOpen className="h-5 w-5" aria-hidden />}
        actions={
          <Link href={`/ask?craft=${encodeURIComponent(craft.slug)}`} className="field-button">
            <MessageCircleQuestion className="h-4 w-4" aria-hidden />
            Ask about this craft
          </Link>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-2 text-xs">
        {craft.giStatus === "GI" ? (
          <span className="rounded-full border border-success-600/25 bg-success-100 px-2.5 py-1 font-semibold text-success-600">GI registered</span>
        ) : null}
        {craft.stateOfPractice.map((state) => (
          <span key={state} className="rounded-full border border-line-200 bg-card px-2.5 py-1 font-medium text-ink-700">
            {state}
          </span>
        ))}
      </div>

      <CraftTabs value={tab} onChange={setTab} />

      <section id={craftPanelId(tab)} role="tabpanel" aria-labelledby={craftTabId(tab)} tabIndex={0} className="mt-4 focus-visible:outline-offset-4" data-testid={`craft-panel-${tab}`}>
        {tab === "overview" ? (
          <div className="panel p-5 md:p-6">
            {craft.description ? <p className="mb-4 text-[15px] leading-7 text-ink-700">{craft.description}</p> : null}
            <ClaimList claims={profile.overview} numbers={numbers} sourcesById={sourcesById} onOpen={onOpen} />
          </div>
        ) : null}

        {tab === "map" ? <CraftMap profile={profile} /> : null}

        {tab === "process" ? (
          profile.stages.length === 0 ? (
            <div className="panel p-5">
              <NoSourceFound />
            </div>
          ) : (
            <motion.ol variants={staggerParent(reduce)} initial="hidden" animate="show" className="relative grid gap-3 [--rail:2rem]">
              {profile.stages
                .slice()
                .sort((a, b) => a.ordinal - b.ordinal)
                .map((stage, index) => (
                  <motion.li key={stage.id} variants={riseItem(reduce)} className="panel grid grid-cols-[var(--rail)_minmax(0,1fr)] gap-x-4 p-4 md:p-5">
                    <span aria-hidden className="grid h-8 w-8 place-items-center justify-self-center rounded-full bg-purple-700 font-display text-sm font-bold text-white">
                      {index + 1}
                    </span>
                    <div className="min-w-0">
                      <h3 className="font-display text-base font-bold text-ink-900">
                        <span className="sr-only">Step {index + 1}: </span>
                        {stage.name}
                      </h3>
                      {stage.durationText ? <p className="mt-0.5 text-xs text-ink-500">{stage.durationText}</p> : null}
                      <div className="mt-2">
                        <ClaimList claims={stage.claims} numbers={numbers} sourcesById={sourcesById} onOpen={onOpen} />
                      </div>
                    </div>
                  </motion.li>
                ))}
            </motion.ol>
          )
        ) : null}

        {tab === "materials" ? (
          profile.materials.length === 0 ? (
            <div className="panel p-5">
              <NoSourceFound />
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {profile.materials.map((material) => (
                <section key={material.id} className="panel p-5">
                  <h3 className="font-display text-base font-bold text-ink-900">{material.name}</h3>
                  {material.description ? <p className="mt-1 text-sm text-ink-500">{material.description}</p> : null}
                  <div className="mt-3">
                    <ClaimList claims={material.claims} numbers={numbers} sourcesById={sourcesById} onOpen={onOpen} />
                  </div>
                </section>
              ))}
            </div>
          )
        ) : null}

        {tab === "science" ? (
          profile.science.length === 0 ? (
            <div className="panel p-5">
              <NoSourceFound />
            </div>
          ) : (
            <ol className="grid gap-3">
              {profile.science.map((reaction) => (
                <li key={reaction.id} className="panel p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="flex items-center gap-2 text-sm font-semibold text-ink-900">
                      <FlaskConical className="h-4 w-4 text-purple-700 dark:text-purple-300" aria-hidden />
                      {reaction.label}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <EvidenceLevelBadge level={reaction.level} />
                      {reaction.balanced ? null : (
                        <span className="rounded-full border border-amber-500/30 bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">Unbalanced</span>
                      )}
                    </span>
                  </div>
                  <ChemEquation equation={reaction.equation} className="mt-3 text-base" />
                  {reaction.conditions ? <p className="mt-2 text-xs text-ink-500">{reaction.conditions}</p> : null}
                  <p className="mt-2 text-xs">
                    {uniqueCitations(reaction.citations).map((citation) => (
                      <CitationChip
                        key={`${citation.sourceId}:${citation.claimId}`}
                        citation={citation}
                        number={numbers.get(citation.sourceId) ?? null}
                        title={sourcesById.get(citation.sourceId)?.title ?? null}
                        onOpen={onOpen}
                      />
                    ))}
                  </p>
                </li>
              ))}
            </ol>
          )
        ) : null}

        {tab === "sources" ? <SourcesTab sources={profile.sources} numbers={numbers} /> : null}
      </section>

      <SourceDialog open={open} onClose={() => setOpen(null)} />
    </>
  );
}

function CraftMap({ profile }: { profile: CraftProfile }) {
  const points: MapPoint[] = profile.locations
    .filter((location) => location.latitude !== null && location.longitude !== null)
    .map((location, index) => ({
      key: location.id,
      pinLabel: String(index + 1),
      countText: null,
      name: location.placeLabel,
      latitude: location.latitude as number,
      longitude: location.longitude as number,
      total: 1,
      caption: locationCaption(location)
    }));
  const unplaced = profile.locations.filter((location) => location.latitude === null || location.longitude === null);

  if (profile.locations.length === 0) {
    return (
      <div className="panel p-5">
        <NoSourceFound />
      </div>
    );
  }

  return (
    <div className="panel p-4 md:p-6">
      <IndiaMapStage points={points} listLabel="Places" countLabel={() => ""} />
      {unplaced.length > 0 ? (
        <ul className="mt-4 grid gap-1 border-t border-line-200 pt-4 text-sm">
          {unplaced.map((location) => (
            <li key={location.id} className="flex flex-wrap items-baseline gap-2">
              <span className="font-medium text-ink-900">{location.placeLabel}</span>
              <span className="text-xs text-ink-500">{locationCaption(location)}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function SourcesTab({ sources, numbers }: { sources: SourceRef[]; numbers: Map<string, number> }) {
  if (sources.length === 0) {
    return (
      <div className="panel p-5">
        <NoSourceFound />
      </div>
    );
  }
  const ordered = sources.slice().sort((a, b) => (numbers.get(a.id) ?? 0) - (numbers.get(b.id) ?? 0));
  return (
    <ol className="panel grid gap-3 p-5">
      {ordered.map((source) => {
        const href = sourceHref(source);
        return (
          <li key={source.id} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-2 text-sm">
            <span className="font-display font-bold tabular-nums text-purple-700 dark:text-purple-300">[{numbers.get(source.id)}]</span>
            <span className="min-w-0">
              {href ? (
                <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-ink-900 hover:text-purple-700 hover:underline">
                  {source.title}
                  <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden />
                </a>
              ) : (
                <span className="font-medium text-ink-900">{source.title}</span>
              )}
              <span className="block text-xs text-ink-500">{[sourceByline(source), sourceHost(href), source.licence].filter(Boolean).join(" · ")}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
