import { statTilesShape } from "@/lib/componentSpecsData";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

export function StatTilesView({ spec, renderUnit }: ComponentViewProps) {
  const stats = parseShape(statTilesShape, spec);
  return (
    <div className={["ws-stats", ...stats.classes].join(" ")}>
      {stats.tiles.map((tile) => (
        <div key={tile.caption} className="mk-stat">
          <span className="t-stat">
            {tile.figure}
            {tile.small ? <small>{tile.small}</small> : null}
          </span>
          <p>{renderUnit(tile.caption)}</p>
        </div>
      ))}
    </div>
  );
}
