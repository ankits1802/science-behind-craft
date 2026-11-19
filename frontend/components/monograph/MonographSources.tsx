import { sourceByline, supportLine } from "@/components/monograph/SourceList";
import { sourceReliabilityLabel } from "@/lib/citations";
import type { MonographDocument, MonographSource } from "@/lib/monographDocument";
import { GRADE_ORDER, sentenceCounts } from "@/lib/monographRenderKit";
import { pageSources } from "@/lib/monographRenderLayout";
import type { SourceReliability } from "@/lib/types";

export const UNGRADED_GROUP = "Other sources";
export const SOURCE_STATUS_ID = "kv-src-status";

export type SourceGroup = { title: string; keys: string[] };

function gradeOf(source: MonographSource): SourceReliability | null {
  return (GRADE_ORDER as readonly string[]).includes(source.grade ?? "") ? (source.grade as SourceReliability) : null;
}

function groupTitle(grade: SourceReliability): string {
  const words = sourceReliabilityLabel(grade).split(" · ")[1] ?? grade;
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function sourceGroups(document: MonographDocument): SourceGroup[] {
  const sources = document.content.sources;
  const keys = pageSources(document);
  const graded = GRADE_ORDER.map((grade) => ({ title: groupTitle(grade), keys: keys.filter((key) => gradeOf(sources[key]) === grade) }));
  const other = { title: UNGRADED_GROUP, keys: keys.filter((key) => gradeOf(sources[key]) === null) };
  return [...graded, other].filter((group) => group.keys.length > 0);
}

export function sourcesDek(count: number): string {
  const noun = count === 1 ? "source" : "sources";
  return `The monograph’s ${count} ${noun}, numbered as they first appear. Select one to light the sentences it supports.`;
}

function SourceRow({ sourceKey, source, count }: { sourceKey: string; source: MonographSource; count: number }) {
  const byline = sourceByline(source);
  const grade = gradeOf(source);
  return (
    <li className="kv-src-li">
      <button type="button" className="src" data-g={sourceKey} aria-pressed="false">
        <b>{source.number}</b>
        <span className="src-main">
          <span className="src-t">{source.fullTitle ?? source.title}</span>
          <small>
            {byline ? <span>{byline}</span> : null}
            {grade ? (
              <span className="relw">
                <span className={`rel ${grade}`} aria-hidden="true" />
                {sourceReliabilityLabel(grade)}
              </span>
            ) : null}
            <span>{supportLine(count)}</span>
          </small>
        </span>
      </button>
      {source.url ? (
        <a className="kv-src-link" href={source.url} rel="noopener" target="_blank">
          Open the source<span className="vh">: {source.title}</span>
        </a>
      ) : null}
    </li>
  );
}

export function MonographSources({ document }: { document: MonographDocument }) {
  const groups = sourceGroups(document);
  const counts = sentenceCounts(document);
  const total = groups.reduce((sum, group) => sum + group.keys.length, 0);
  if (!total) return null;
  return (
    <div className="bx bx-rm">
      <div className="screen" data-aid="cite">
        <div className="wrap">
          <p className="src-dek">{sourcesDek(total)}</p>
          <div className="sources kv-sources">
            {groups.map((group) => (
              <div className="src-group" key={group.title}>
                <h3>{group.title}</h3>
                <ul>
                  {group.keys.map((key) => (
                    <SourceRow key={key} sourceKey={key} source={document.content.sources[key]} count={counts.get(key) ?? 0} />
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div id={SOURCE_STATUS_ID} className="kv-src-status" role="status" />
        </div>
      </div>
    </div>
  );
}
