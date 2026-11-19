import type { ReactNode } from "react";

import { conceptAtlasShape, type ConceptGroup, type ConceptRow } from "@/lib/componentSpecsData";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

import { TextLineView } from "./DataParts";

type RenderUnit = (ref: string) => ReactNode;

export function conceptMeta(row: Pick<ConceptRow, "place" | "family" | "sentences">): string {
  return `${row.place} · ${row.family} · named in ${row.sentences} cited sentence${row.sentences === 1 ? "" : "s"}`;
}

function Rows({ rows, renderUnit }: { rows: ConceptRow[]; renderUnit: RenderUnit }) {
  return (
    <ol className="res-list">
      {rows.map((row) => (
        <li key={row.name} className="res-row">
          <span className="res-name kv-res-name">{row.name}</span>
          <span className="res-meta">{conceptMeta(row)}</span>
          <TextLineView line={row.sentence} renderUnit={renderUnit} />
        </li>
      ))}
    </ol>
  );
}

function Group({ group, renderUnit }: { group: ConceptGroup; renderUnit: RenderUnit }) {
  return (
    <div className="res-group kv-ss" id={group.id}>
      <div className="res-concept">
        <h3>{renderUnit(group.title)}</h3>
        <p>{renderUnit(group.text)}</p>
        <p className="cooc">{renderUnit(group.together)}</p>
      </div>
      <Rows rows={group.first} renderUnit={renderUnit} />
      {group.more.length ? (
        <details className="kv-more">
          <summary>
            <span className="kv-more-o">{`Show all ${group.first.length + group.more.length}`}</span>
            <span className="kv-more-c">Show fewer</span>
          </summary>
          <Rows rows={group.more} renderUnit={renderUnit} />
        </details>
      ) : null}
    </div>
  );
}

export function ConceptAtlasView({ spec, renderUnit }: ComponentViewProps) {
  const atlas = parseShape(conceptAtlasShape, spec);
  return (
    <div className="kv-shared">
      <h3 className="kv-sub-h">{renderUnit(atlas.title)}</h3>
      <p className="kv-sub-d">{renderUnit(atlas.description)}</p>
      <div className="results kv-results">
        {atlas.groups.map((group) => (
          <Group key={group.id} group={group} renderUnit={renderUnit} />
        ))}
      </div>
    </div>
  );
}
