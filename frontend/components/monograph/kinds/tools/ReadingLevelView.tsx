"use client";

import { useId, useMemo } from "react";

import { LegacyScope } from "@/components/monograph/LegacyScope";
import { parseToolSpec, readingLevelSpecShape } from "@/lib/componentSpecsTools";
import type { ComponentViewProps } from "@/lib/componentViewContract";

export function ReadingLevelView({ spec, renderUnit }: ComponentViewProps) {
  const level = useMemo(() => parseToolSpec(readingLevelSpecShape, spec), [spec]);
  const titleId = useId();
  return (
    <LegacyScope scope="sa">
      <details className="kv-alt-teen">
        <summary>
          <span className="kv-alt-s">{level.summary}</span>
          <span className="kv-alt-d">{level.detail}</span>
        </summary>
        <section className="twin-col" data-level={level.level} aria-labelledby={titleId}>
          <header className="twin-h">
            <h2 className="twin-t" id={titleId}>
              {renderUnit(level.title)}
            </h2>
          </header>
          <p className="t-lede twin-lede">{renderUnit(level.lede)}</p>
        </section>
      </details>
    </LegacyScope>
  );
}
