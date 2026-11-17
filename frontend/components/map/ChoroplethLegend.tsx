import { DatasetCredit } from "@/components/DatasetCredit";
import { CHOROPLETH_TONES, NO_DATA_TONE } from "@/components/map/DistrictLayer";
import type { MapLayer } from "@/lib/regionContract";
import { layerCaption, layerClassLabels, layerSummary, NO_DATA_LABEL, toneIndex } from "@/lib/regionView";
import { cn } from "@/lib/utils";

export function choroplethTone(classIndex: number, classCount: number): string {
  return CHOROPLETH_TONES[toneIndex(classIndex, classCount, CHOROPLETH_TONES.length)];
}

export function Swatch({ className }: { className: string }) {
  return (
    <svg width={14} height={14} aria-hidden className="shrink-0">
      <rect x={0.5} y={0.5} width={13} height={13} rx={3} className={cn("stroke-line-200", className)} />
    </svg>
  );
}

export function ChoroplethLegend({ layer }: { layer: MapLayer }) {
  const labels = layerClassLabels(layer);
  return (
    <div className="mt-4 grid gap-2 border-t border-line-200 pt-4" data-testid="choropleth-legend">
      <p className="text-sm font-semibold text-ink-900">{layer.layer.title}</p>
      <p className="sr-only">{layerSummary(layer)}</p>
      <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs tabular-nums text-ink-700">
        {labels.map((label, index) => (
          <li key={label} className="inline-flex items-center gap-1.5">
            <Swatch className={choroplethTone(index, labels.length)} />
            {label}
          </li>
        ))}
        <li className="inline-flex items-center gap-1.5">
          <Swatch className={NO_DATA_TONE} />
          {NO_DATA_LABEL}
        </li>
      </ul>
      <p className="text-xs text-ink-500">{layerCaption(layer)}</p>
      <DatasetCredit dataset={layer.dataset} />
    </div>
  );
}
