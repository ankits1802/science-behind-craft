import type { ComponentType } from "react";

import { GeneratedExplainer } from "@/components/answer/play/GeneratedExplainer";
import { WhatIfLab } from "@/components/answer/play/WhatIfLab";
import type { SimulationBlock, WhatIfBlock } from "@/lib/explainerPlay";

export const PLAY_RENDERERS: {
  simulation: ComponentType<{ block: SimulationBlock }>;
  what_if: ComponentType<{ block: WhatIfBlock }>;
} = {
  simulation: GeneratedExplainer,
  what_if: WhatIfLab
};
