import type { ComponentType } from "react";

import { GeneratedExplainer } from "@/components/answer/play/GeneratedExplainer";
import { KitFigureView } from "@/components/answer/play/KitFigureView";
import { WhatIfLab } from "@/components/answer/play/WhatIfLab";
import type { KitFigureBlock } from "@/lib/explainerKit";
import type { SimulationBlock, WhatIfBlock } from "@/lib/explainerPlay";

export const PLAY_RENDERERS: {
  simulation: ComponentType<{ block: SimulationBlock }>;
  what_if: ComponentType<{ block: WhatIfBlock }>;
  kit_figure: ComponentType<{ block: KitFigureBlock }>;
} = {
  simulation: GeneratedExplainer,
  what_if: WhatIfLab,
  kit_figure: KitFigureView
};
