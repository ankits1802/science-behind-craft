"use client";

import { FOREIGN_EXTRA, MapLegend, SALT_EXTRA, WATER_EXTRA, type LegendExtra } from "@/components/map/ChoroplethLegend";
import { DatasetCredit } from "@/components/DatasetCredit";
import { MineralSymbol, mineralColour } from "@/components/map/physical/MineralsLayer";
import { RankedList, type RankedRow } from "@/components/map/RankedList";
import { ELEVATION_BREAKS } from "@/lib/mapPalettes";
import { formatRange } from "@/lib/measure";
import { elevationBands, mineralKeyRows, tally, type DatasetRow, type MineralKeyRow, type MineralSite, type MineralsFile, type ReliefFile, type RiversFile } from "@/lib/mapPhysical";

export function LayerCredits({ datasets }: { datasets: readonly DatasetRow[] }) {
  return (
    <ul className="grid gap-2 border-t border-rule pt-3" data-testid="layer-credits">
      {datasets.map((row) => (
        <li key={row.file}>
          <DatasetCredit dataset={row} />
        </li>
      ))}
    </ul>
  );
}

export function reliefSteps(breaks: readonly number[] = ELEVATION_BREAKS): { label: string; colour: string }[] {
  return elevationBands(breaks).map((band, at) => ({ label: formatRange(band.min, band.max, "m") ?? "", colour: `var(--elevation-${at + 1})` }));
}

export function peakRows(file: ReliefFile): RankedRow[] {
  return file.peaks.map((peak) => ({ key: peak.name, name: peak.name, value: peak.elevation, display: `${peak.elevation.toLocaleString("en-IN")} m` }));
}

export function ReliefKey() {
  return <MapLegend title="Elevation" steps={reliefSteps()} extras={[FOREIGN_EXTRA, WATER_EXTRA]} note="Band edges are the contours; the shading is lit from the north-west." />;
}

export function ReliefSide({ file }: { file: ReliefFile }) {
  return (
    <>
      <ReliefKey />
      <div className="grid gap-2">
        <p className="font-ui text-label text-ink-1">Spot heights</p>
        <p className="font-ui text-caption text-ink-3">{`The ${file.peaks.length} named summits inside the outline, by height; the highest are marked on the map.`}</p>
        <RankedList rows={peakRows(file)} label="Named summits by height" series="var(--chart-series)" all={{ label: `Show all ${file.peaks.length}` }} />
      </div>
      <LayerCredits datasets={file.datasets} />
    </>
  );
}

const RIVER_KEY: readonly { key: string; label: string; width: number }[] = [
  { key: "major", label: "Major rivers", width: 1.9 },
  { key: "rivers", label: "Rivers", width: 1.35 },
  { key: "tributaries", label: "Tributaries and smaller rivers", width: 0.85 }
];

function RiverKey() {
  return (
    <ul className="grid gap-1.5 font-ui text-caption text-ink-2" aria-label="Line widths">
      {RIVER_KEY.map((row) => (
        <li key={row.key} className="inline-flex items-center gap-2">
          <svg width={18} height={12} aria-hidden className="shrink-0 [forced-color-adjust:none]">
            <line x1={1} y1={6} x2={17} y2={6} stroke="var(--map-river)" strokeWidth={row.width} strokeLinecap="round" />
          </svg>
          {row.label}
        </li>
      ))}
    </ul>
  );
}

const LAKE_EXTRA: LegendExtra = { key: "lake", label: "Lakes and reservoirs", fill: "var(--map-water)", edge: "var(--map-river)" };

export function RiversKey() {
  return (
    <div className="grid gap-2 border-t border-rule pt-3" data-testid="rivers-key">
        <p className="font-ui text-label text-ink-1">Rivers and lakes</p>
        <RiverKey />
        <ul className="grid gap-1.5 font-ui text-caption text-ink-2">
          {[LAKE_EXTRA, SALT_EXTRA, FOREIGN_EXTRA].map((extra) => (
            <li key={extra.key} className="inline-flex items-center gap-2">
              <svg width={18} height={12} aria-hidden className="shrink-0 [forced-color-adjust:none]">
                <rect x={0.5} y={0.5} width={17} height={11} fill={extra.fill} stroke={extra.edge ?? "var(--map-coast)"} strokeDasharray={extra.dashed ? "1 2" : undefined} />
              </svg>
              {extra.label}
            </li>
          ))}
        </ul>
    </div>
  );
}

export function RiversSide({ file }: { file: RiversFile }) {
  const named = [...file.labels].sort((a, b) => a.tier - b.tier || a.text.localeCompare(b.text, "en"));
  return (
    <>
      <RiversKey />
      <div className="grid gap-2">
        <p className="font-ui text-label text-ink-1">{`${named.length} rivers named on the map`}</p>
        <ul className="grid grid-cols-2 gap-x-4 gap-y-1 border-t border-rule pt-2 font-reading text-body-sm italic text-ink-1" data-testid="rivers-named">
          {named.map((label) => (
            <li key={label.text}>{label.text}</li>
          ))}
        </ul>
      </div>
      <LayerCredits datasets={file.datasets} />
    </>
  );
}

export function MineralKey({ rows }: { rows: readonly MineralKeyRow[] }) {
  const largest = Math.max(0, ...rows.map((row) => row.count));
  return (
    <ol className="grid border-b border-rule font-ui text-ui" aria-label="Deposits in each class" data-testid="mineral-key">
      {rows.map((row, at) => (
        <li key={row.id} className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-2.5 gap-y-1 border-t border-rule py-[7px]">
          <MineralSymbol classIndex={at} size={9} />
          <span className="min-w-0 text-ink-1">{row.label}</span>
          <b className="text-end font-medium text-ink-2 [font-variant-numeric:lining-nums_tabular-nums]">{row.count}</b>
          <span className="relative col-start-2 col-end-4 h-1.5 bg-rule" aria-hidden>
            <i className="absolute inset-y-0 start-0" style={{ width: `${largest ? ((row.count / largest) * 100).toFixed(1) : 0}%`, backgroundColor: mineralColour(at) }} />
          </span>
        </li>
      ))}
    </ol>
  );
}

export function MineralsSide({ file, sites }: { file: MineralsFile; sites: readonly MineralSite[] }) {
  const states: RankedRow[] = tally(sites.map((site) => site.state)).map((row) => ({ key: row.key, name: row.label, value: row.count }));
  const statuses = tally(sites.map((site) => site.status));
  return (
    <>
      <MineralKey rows={mineralKeyRows(file, sites)} />
      <div className="grid gap-2">
        <p className="font-ui text-label text-ink-1">Deposits in each state</p>
        <RankedList rows={states} label="Deposits in each state" series="var(--chart-series)" emphKey={states[0]?.key ?? null} all={{ label: `Show all ${states.length}` }} />
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-rule pt-3 font-ui sm:grid-cols-3" data-testid="mineral-status">
        {statuses.map((row) => (
          <div key={row.key} className="flex flex-col-reverse">
            <dt className="text-caption text-ink-3">{row.label}</dt>
            <dd className="m-0 text-h4 text-ink-1 [font-variant-numeric:lining-nums_tabular-nums]">{row.count}</dd>
          </div>
        ))}
      </dl>
      <LayerCredits datasets={[file.source]} />
    </>
  );
}
