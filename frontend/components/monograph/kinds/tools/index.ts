import { AskNextView } from "@/components/monograph/kinds/tools/AskNextView";
import { ExplainerView } from "@/components/monograph/kinds/tools/ExplainerView";
import { GeneratorView } from "@/components/monograph/kinds/tools/GeneratorView";
import { LanguageSwitchView } from "@/components/monograph/kinds/tools/LanguageSwitchView";
import { QuizView } from "@/components/monograph/kinds/tools/QuizView";
import { ReadingLevelView } from "@/components/monograph/kinds/tools/ReadingLevelView";
import type { ToolKind } from "@/lib/componentSpecsTools";
import type { ComponentView } from "@/lib/componentViewContract";

export const VIEWS: Readonly<Record<ToolKind, ComponentView>> = {
  explainer: ExplainerView,
  quiz: QuizView,
  ask_next: AskNextView,
  language_switch: LanguageSwitchView,
  reading_level: ReadingLevelView,
  generator: GeneratorView
};
