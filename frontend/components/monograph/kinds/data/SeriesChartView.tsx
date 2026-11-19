import type { ReactNode } from "react";

import { SpecDrawing } from "@/components/monograph/kinds/plates/SpecDrawing";
import { pythonJson, type SeriesChart, type SeriesTable } from "@/lib/componentSpecsData";

import { FigureHeadView, labelledBy, PlacedLabel } from "./DataParts";

type RenderUnit = (ref: string) => ReactNode;

function SeriesTableView({ table, download, renderUnit }: { table: SeriesTable; download: SeriesChart["download"]; renderUnit: RenderUnit }) {
  return (
    <details className="rain-table">
      <summary>{table.summary}</summary>
      <div className="tw">
        <table>
          <caption className="vh">{table.caption}</caption>
          <thead>
            <tr>
              {table.head.map((unit) => (
                <th key={unit} scope="col">
                  {renderUnit(unit)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row) => (
              <tr key={row.head}>
                <th scope="row">{renderUnit(row.head)}</th>
                {row.cells.map((cell, index) => (
                  <td key={cell ?? `empty-${index}`}>{cell ? renderUnit(cell) : null}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="actions csv start" data-count="1">
        <a className="btn sm" href={download.href} download={download.fileName}>
          {download.label}
        </a>
      </div>
    </details>
  );
}

export function SeriesChartView({ chart, renderUnit }: { chart: SeriesChart; renderUnit: RenderUnit }) {
  const plot = chart.plot;
  return (
    <figure className={chart.classes.join(" ")} aria-labelledby={labelledBy(chart.head)}>
      <FigureHeadView head={chart.head} renderUnit={renderUnit} />
      <div className={plot.classes.join(" ")} tabIndex={0} role="img" aria-label={plot.label} data-comp={plot.comp} data-series={pythonJson(plot.series)}>
        <SpecDrawing element={plot.drawing} />
        {plot.labels.map((label, index) => (
          <PlacedLabel key={index} label={label} />
        ))}
        <div className="r2-tip" hidden></div>
      </div>
      <ol className="rain-events">
        {chart.events.map((unit) => (
          <li key={unit}>{renderUnit(unit)}</li>
        ))}
      </ol>
      <SeriesTableView table={chart.table} download={chart.download} renderUnit={renderUnit} />
      <p className="src-line">{renderUnit(chart.source)}</p>
    </figure>
  );
}
