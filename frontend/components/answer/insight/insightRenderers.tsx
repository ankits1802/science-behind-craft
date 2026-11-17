import type { ComponentType } from "react";

import { ClimateRiskBlockView } from "@/components/answer/insight/ClimateRiskView";
import { MarketGiView } from "@/components/answer/insight/MarketGiView";
import { MeasureView } from "@/components/answer/insight/MeasureView";
import type { ClimateRiskBlock, MarketGiBlock, MeasureBlock } from "@/lib/explainerInsight";

export const INSIGHT_RENDERERS: {
  measure: ComponentType<{ block: MeasureBlock }>;
  market_gi: ComponentType<{ block: MarketGiBlock }>;
  climate_risk: ComponentType<{ block: ClimateRiskBlock }>;
} = {
  measure: MeasureView,
  market_gi: MarketGiView,
  climate_risk: ClimateRiskBlockView
};
