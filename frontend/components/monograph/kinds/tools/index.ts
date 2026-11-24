import { NearAskNextView, NearExplainerView, NearGeneratorView, NearLanguageSwitchView, NearQuizView, NearReadingLevelView } from "@/components/monograph/kinds/nearViews";
import type { ToolKind } from "@/lib/componentSpecsTools";
import type { ComponentView } from "@/lib/componentViewContract";

export const VIEWS: Readonly<Record<ToolKind, ComponentView>> = {
  explainer: NearExplainerView,
  quiz: NearQuizView,
  ask_next: NearAskNextView,
  language_switch: NearLanguageSwitchView,
  reading_level: NearReadingLevelView,
  generator: NearGeneratorView
};
