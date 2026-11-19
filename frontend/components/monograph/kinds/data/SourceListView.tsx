import { sourceListShape, type ListedSource, type SourceListing } from "@/lib/componentSpecsData";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

export function supportsLine(sentences: number): string {
  return `Supports ${sentences} sentence${sentences === 1 ? "" : "s"} here`;
}

function SourceEntry({ source }: { source: ListedSource }) {
  return (
    <li className="kv-src-li">
      <button type="button" className="src" data-g={source.key} aria-pressed="false">
        <b>{source.number}</b>
        <span className="src-main">
          <span className="src-t">{source.title}</span>
          <small>
            <span>{source.meta}</span>
            <span className="relw">
              <span className={`rel ${source.grade}`} aria-hidden="true"></span>
              {source.gradeLabel}
            </span>
            <span>{supportsLine(source.sentences)}</span>
          </small>
          {source.margin ? (
            <span className="mg">
              <span>{source.margin}</span>
            </span>
          ) : null}
        </span>
      </button>
      <a className="kv-src-link" href={source.url} rel="noopener" target="_blank">
        Open the source<span className="vh">{source.linkLabel}</span>
      </a>
    </li>
  );
}

function Listing({ listing, renderUnit }: { listing: SourceListing; renderUnit: ComponentViewProps["renderUnit"] }) {
  return (
    <div className={listing.id} id={listing.id}>
      <h3 className="kv-sub-h">{renderUnit(listing.title)}</h3>
      <p className="kv-sub-d">{renderUnit(listing.description)}</p>
      <details className="kv-more kv-src-more">
        <summary>
          <span className="kv-more-o">{listing.openLabel}</span>
          <span className="kv-more-c">{listing.closeLabel}</span>
        </summary>
        <div className="sources kv-sources">
          <div className="src-group">
            <ul>
              {listing.sources.map((source) => (
                <SourceEntry key={source.key} source={source} />
              ))}
            </ul>
          </div>
        </div>
      </details>
    </div>
  );
}

export function SourceListView({ spec, renderUnit }: ComponentViewProps) {
  const list = parseShape(sourceListShape, spec);
  if (list.listing) return <Listing listing={list.listing} renderUnit={renderUnit} />;
  return <div className="kv-src-status" role="status" id={list.statusId ?? undefined}></div>;
}
