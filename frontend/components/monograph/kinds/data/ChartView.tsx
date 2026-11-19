import type { ReactNode } from "react";

import { SpecDrawing } from "@/components/monograph/kinds/plates/SpecDrawing";
import { chartShape, type BarRow, type DotsChart, type FigureChart, type RowsChart } from "@/lib/componentSpecsData";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

import { FigureHeadView, labelledBy, TextLineView } from "./DataParts";
import { SeriesChartView } from "./SeriesChartView";

type RenderUnit = (ref: string) => ReactNode;

const SHARE_DIGITS = 2;
const SMALL_BAR_WIDTH = "2px";

export function barShare(value: number, largest: number): string {
  return `${Number(((value / largest) * 100).toFixed(SHARE_DIGITS))}%`;
}

function barStyle(row: BarRow, largest: number): Record<string, string> {
  const width = barShare(row.value, largest);
  return row.value < largest ? { width, minWidth: SMALL_BAR_WIDTH } : { width };
}

function DotsView({ dots }: { dots: DotsChart }) {
  return (
    <div className={dots.classes.join(" ")} role="img" aria-label={dots.label}>
      {Array.from({ length: dots.total }, (_, index) => (
        <i key={index} className={index < dots.marked ? "on" : ""}></i>
      ))}
    </div>
  );
}

function RowsView({ chart, renderUnit }: { chart: RowsChart; renderUnit: RenderUnit }) {
  const largest = Math.max(...chart.rows.map((row) => row.value));
  return (
    <figure className={chart.classes.join(" ")} aria-labelledby={labelledBy(chart.head)}>
      <FigureHeadView head={chart.head} renderUnit={renderUnit} />
      {chart.rows.map((row) => (
        <div key={row.label} className="yard-row">
          <span>{row.label}</span>
          <span className={row.emphasis ? "yb emph" : "yb"} style={barStyle(row, largest)}></span>
          <b>{row.shown}</b>
        </div>
      ))}
      <p className="src-line">{renderUnit(chart.source)}</p>
    </figure>
  );
}

function FigureView({ chart, renderUnit }: { chart: FigureChart; renderUnit: RenderUnit }) {
  return (
    <figure className={chart.classes.join(" ")} aria-labelledby={labelledBy(chart.head)}>
      <FigureHeadView head={chart.head} renderUnit={renderUnit} />
      <SpecDrawing element={chart.drawing} />
      <TextLineView line={chart.source} renderUnit={renderUnit} />
    </figure>
  );
}

export function ChartView({ spec, renderUnit }: ComponentViewProps) {
  const chart = parseShape(chartShape, spec);
  if (chart.drawing) return <SpecDrawing element={chart.drawing} />;
  if (chart.dots) return <DotsView dots={chart.dots} />;
  if (chart.rows) return <RowsView chart={chart.rows} renderUnit={renderUnit} />;
  if (chart.figure) return <FigureView chart={chart.figure} renderUnit={renderUnit} />;
  if (chart.series) return <SeriesChartView chart={chart.series} renderUnit={renderUnit} />;
  throw new RangeError(`A ${chart.form} chart has its part`);
}
