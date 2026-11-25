"use client";

import { nearBlock } from "@/components/answer/nearBlock";
import { Skeleton } from "@/components/ui/Skeleton";
import type { ComponentView, ComponentViewProps } from "@/lib/componentViewContract";

export const NEAR_RESERVE_LABEL = "Drawing the figure";

const RESERVE = <Skeleton shape="chart" label={NEAR_RESERVE_LABEL} />;

function nearView(load: () => Promise<ComponentView>): ComponentView {
  const Near = nearBlock<ComponentViewProps>(load, RESERVE);
  return function NearView(props: ComponentViewProps) {
    return <Near {...props} />;
  };
}

export const NearWhyHereView = nearView(() => import("@/components/monograph/kinds/place/WhyHereView").then((loaded) => loaded.WhyHereView));
export const NearMapLayerView = nearView(() => import("@/components/monograph/kinds/general/MapLayerView").then((loaded) => loaded.MapLayerView));
export const NearTimelineMapView = nearView(() => import("@/components/monograph/kinds/general/TimelineMapDeclaredView").then((loaded) => loaded.TimelineMapDeclaredView));
export const NearExplainerView = nearView(() => import("@/components/monograph/kinds/tools/ExplainerView").then((loaded) => loaded.ExplainerView));
export const NearQuizView = nearView(() => import("@/components/monograph/kinds/tools/QuizView").then((loaded) => loaded.QuizView));
export const NearAskNextView = nearView(() => import("@/components/monograph/kinds/tools/AskNextView").then((loaded) => loaded.AskNextView));
export const NearLanguageSwitchView = nearView(() => import("@/components/monograph/kinds/tools/LanguageSwitchView").then((loaded) => loaded.LanguageSwitchView));
export const NearReadingLevelView = nearView(() => import("@/components/monograph/kinds/tools/ReadingLevelView").then((loaded) => loaded.ReadingLevelView));
export const NearGeneratorView = nearView(() => import("@/components/monograph/kinds/tools/GeneratorView").then((loaded) => loaded.GeneratorView));
