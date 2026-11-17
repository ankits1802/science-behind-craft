"use client";

import { motion } from "framer-motion";

import { StripLine } from "@/components/answer/place/StripLine";
import { EASE_OUT } from "@/components/guide/guideMotion";
import { significanceText, slopeText, TREND_WORDS, trendBar, trendContext, type TrendGroup, type TrendVariable } from "@/lib/climateView";
import type { ClimateTrend } from "@/lib/explainerInsight";
import { cn } from "@/lib/utils";

const BAR_TONE: Record<TrendVariable, { solid: string; open: string }> = {
  annual_precipitation: {
    solid: "bg-errand-600 dark:bg-errand-300",
    open: "border border-dashed border-errand-600 bg-errand-200 dark:border-errand-300 dark:bg-errand-900"
  },
  annual_mean_temperature: {
    solid: "bg-steward-600 dark:bg-steward-300",
    open: "border border-dashed border-steward-600 bg-steward-200 dark:border-steward-300 dark:bg-steward-900"
  }
};

function Bar({ trend, domain, reduce }: { trend: ClimateTrend; domain: number; reduce: boolean }) {
  const bar = trendBar(trend.slopePerDecade, domain);
  const tone = BAR_TONE[trend.variable];
  return (
    <div aria-hidden className="relative h-3 min-w-0 rounded-full bg-field-100" data-testid="trend-track">
      <motion.span
        className={cn("absolute inset-y-0 rounded-full", trend.significant ? tone.solid : tone.open)}
        style={{ left: `${bar.left}%`, width: `${bar.width}%`, transformOrigin: bar.rising ? "left center" : "right center" }}
        initial={reduce ? false : { scaleX: 0 }}
        whileInView={{ scaleX: 1 }}
        viewport={{ once: true, amount: 0.6 }}
        transition={{ duration: reduce ? 0 : 0.7, ease: EASE_OUT }}
        data-testid="trend-bar"
        data-left={bar.left}
        data-width={bar.width}
        data-significant={trend.significant ? "true" : "false"}
      />
      <span className="absolute -inset-y-1 left-1/2 w-px bg-ink-500" />
    </div>
  );
}

function TrendRow({ trend, domain, reduce }: { trend: ClimateTrend; domain: number; reduce: boolean }) {
  const label = (
    <span className="grid min-w-0">
      <span className="break-words text-sm font-semibold text-ink-900">{trend.district.name}</span>
      <span className="text-xs text-ink-500">{trend.district.stateName}</span>
    </span>
  );
  return (
    <li className="min-w-0" data-testid="trend-row">
      <StripLine label={label}>
        <Bar trend={trend} domain={domain} reduce={reduce} />
        <p className="mt-1.5 flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-0.5 text-sm">
          <span className="font-semibold tabular-nums text-ink-900" data-testid="trend-slope">
            {slopeText(trend)}
          </span>
          <span className="text-xs font-semibold text-ink-500" data-testid="trend-significance">
            {significanceText(trend)}
          </span>
        </p>
        <p className="text-xs text-ink-500" data-testid="trend-context">
          {trendContext(trend)}
        </p>
      </StripLine>
    </li>
  );
}

export function TrendChart({ group, reduce }: { group: TrendGroup; reduce: boolean }) {
  const words = TREND_WORDS[group.variable];
  return (
    <figure className="m-0 grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2" data-testid="trend-chart" data-variable={group.variable}>
      <figcaption className="text-sm font-bold text-ink-900">{words.title}</figcaption>
      <StripLine label={null}>
        <div aria-hidden className="grid grid-cols-[repeat(3,minmax(0,1fr))] text-[11px] font-semibold text-ink-500" data-testid="trend-axis">
          <span>{words.lower}</span>
          <span className="text-center">0</span>
          <span className="text-right">{words.higher}</span>
        </div>
      </StripLine>
      <ul className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3">
        {group.trends.map((trend) => (
          <TrendRow key={`${trend.district.districtLgd}-${trend.variable}`} trend={trend} domain={group.domain} reduce={reduce} />
        ))}
      </ul>
    </figure>
  );
}
