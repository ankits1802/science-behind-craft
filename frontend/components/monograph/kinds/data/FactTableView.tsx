import { factTableShape } from "@/lib/componentSpecsData";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

export function FactTableView({ spec, renderUnit }: ComponentViewProps) {
  const table = parseShape(factTableShape, spec);
  return (
    <section className="chapter" id={table.id} aria-labelledby={table.titleId}>
      <div className="spread railed">
        <div className="rail">
          <span className="numeral">{table.numeral}</span>
        </div>
        <div className="wide">
          <p className="chapter-no in-main">{renderUnit(table.chapterNo)}</p>
          <h2 className="t-h2" id={table.titleId}>
            {renderUnit(table.title)}
          </h2>
        </div>
      </div>
      <dl className="glance">
        {table.rows.map((row) => (
          <div key={row.term}>
            <dt>{renderUnit(row.term)}</dt>
            <dd>{renderUnit(row.value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
