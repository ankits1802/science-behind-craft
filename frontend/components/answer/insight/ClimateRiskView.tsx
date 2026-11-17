"use client";

import { TrendChart } from "@/components/answer/insight/TrendChart";
import { CitedText } from "@/components/answer/ProseBlockView";
import { DatasetCredit } from "@/components/DatasetCredit";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { groundwaterLabel, groundwaterReading, TREND_METHOD_TEXT, trendGroups } from "@/lib/climateView";
import type { ClimateRiskBlock, GroundwaterValue } from "@/lib/explainerInsight";

const SUBHEAD = "text-[11px] font-semibold uppercase tracking-wide text-ink-500";

function Groundwater({ values }: { values: readonly GroundwaterValue[] }) {
  return (
    <div className="grid min-w-0 gap-2" data-testid="groundwater">
      <h4 className={SUBHEAD}>Groundwater</h4>
      <ul className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2 sm:grid-cols-[repeat(2,minmax(0,1fr))]">
        {values.map((value) => (
          <li key={`${value.district.districtLgd}-${value.datasetCode}-${value.variable}`} className="grid min-w-0 gap-0.5 rounded-md border border-line-200 bg-surface-50 p-3" data-testid="groundwater-value">
            <span className="text-xs font-semibold text-ink-500">
              {groundwaterLabel(value)} · {value.district.name}
            </span>
            <span className="break-words text-base font-bold tabular-nums text-ink-900">{groundwaterReading(value)}</span>
            <span className="text-[11px] text-ink-500">{[value.period, value.resolution].join(" · ")}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ClimateRiskView({ block, reduce }: { block: ClimateRiskBlock; reduce: boolean }) {
  const groups = trendGroups(block.trends);
  if (groups.length === 0 && block.groundwater.length === 0) return null;
  const trendCodes = new Set(block.trends.map((trend) => trend.datasetCode));
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4" data-testid="climate-risk">
      {groups.map((group) => (
        <TrendChart key={group.variable} group={group} reduce={reduce} />
      ))}
      {block.groundwater.length > 0 ? <Groundwater values={block.groundwater} /> : null}
      {block.meaning.length > 0 ? (
        <div className="grid min-w-0 gap-1.5" data-testid="climate-meaning">
          <h4 className={SUBHEAD}>For the craft</h4>
          <CitedText id={`${block.id}-meaning`} sentences={block.meaning} className="text-sm leading-7 text-ink-700" />
        </div>
      ) : null}
      <div className="grid min-w-0 gap-2 border-t border-line-200 pt-3">
        {block.datasets.map((dataset) => (
          <DatasetCredit key={dataset.code} dataset={dataset} methods={trendCodes.has(dataset.code) ? [TREND_METHOD_TEXT] : []} />
        ))}
      </div>
    </div>
  );
}

export function ClimateRiskBlockView({ block }: { block: ClimateRiskBlock }) {
  const reduce = useAppReducedMotion();
  return <ClimateRiskView block={block} reduce={reduce} />;
}
