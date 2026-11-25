"use client";

import { useEffect, useState } from "react";

import { nearBlock } from "@/components/answer/nearBlock";
import { afterLoad, whenIdle } from "@/components/monograph/useShellTrigger";
import { Skeleton } from "@/components/ui/Skeleton";
import { mapLayerSpecShape, parsedSpec } from "@/lib/componentSpecsGeneral";
import { timelineMapFiles, timelineMapSpecShape } from "@/lib/componentSpecsTimelineMap";
import { physicalLayer } from "@/lib/mapPhysical";
import type { ComponentView, ComponentViewProps } from "@/lib/componentViewContract";

export const NEAR_RESERVE_LABEL = "Drawing the figure";

const RESERVE = <Skeleton shape="chart" label={NEAR_RESERVE_LABEL} />;
const NO_FILES = (): readonly string[] => [];

type FilesOf = (spec: unknown) => readonly string[];

function usePageIdle(): boolean {
  const [idle, setIdle] = useState(false);
  useEffect(() => {
    let stopIdle: () => void = () => undefined;
    const settle = () => setIdle(true);
    const stopLoad = afterLoad(window, document, () => {
      if (typeof window.requestIdleCallback === "function") stopIdle = whenIdle(window, settle);
      else settle();
    });
    return () => {
      stopLoad();
      stopIdle();
    };
  }, []);
  return idle;
}

export function PrefetchedFiles({ files }: { files: readonly string[] }) {
  return files.map((href) => <link key={href} rel="prefetch" as="fetch" crossOrigin="anonymous" href={href} />);
}

function IdleFiles({ files }: { files: readonly string[] }) {
  const idle = usePageIdle();
  return idle && files.length > 0 ? <PrefetchedFiles files={files} /> : null;
}

function nearView(load: () => Promise<ComponentView>, filesOf: FilesOf = NO_FILES): ComponentView {
  const Near = nearBlock<ComponentViewProps>(load, RESERVE);
  return function NearView(props: ComponentViewProps) {
    return (
      <>
        <IdleFiles files={filesOf(props.spec)} />
        <Near {...props} />
      </>
    );
  };
}

export function timelineMapPrefetched(spec: unknown): readonly string[] {
  const map = parsedSpec(timelineMapSpecShape, spec);
  return map ? timelineMapFiles(map) : [];
}

export function placesMapPrefetched(spec: unknown): readonly string[] {
  return parsedSpec(mapLayerSpecShape, spec) ? [physicalLayer("relief").asset, physicalLayer("rivers").asset] : [];
}

export const NearWhyHereView = nearView(() => import("@/components/monograph/kinds/place/WhyHereView").then((loaded) => loaded.WhyHereView));
export const NearMapLayerView = nearView(() => import("@/components/monograph/kinds/general/MapLayerView").then((loaded) => loaded.MapLayerView), placesMapPrefetched);
export const NearTimelineMapView = nearView(() => import("@/components/monograph/kinds/general/TimelineMapDeclaredView").then((loaded) => loaded.TimelineMapDeclaredView), timelineMapPrefetched);
export const NearExplainerView = nearView(() => import("@/components/monograph/kinds/tools/ExplainerView").then((loaded) => loaded.ExplainerView));
export const NearQuizView = nearView(() => import("@/components/monograph/kinds/tools/QuizView").then((loaded) => loaded.QuizView));
export const NearAskNextView = nearView(() => import("@/components/monograph/kinds/tools/AskNextView").then((loaded) => loaded.AskNextView));
export const NearLanguageSwitchView = nearView(() => import("@/components/monograph/kinds/tools/LanguageSwitchView").then((loaded) => loaded.LanguageSwitchView));
export const NearReadingLevelView = nearView(() => import("@/components/monograph/kinds/tools/ReadingLevelView").then((loaded) => loaded.ReadingLevelView));
export const NearGeneratorView = nearView(() => import("@/components/monograph/kinds/tools/GeneratorView").then((loaded) => loaded.GeneratorView));
