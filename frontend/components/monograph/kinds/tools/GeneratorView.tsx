"use client";

import { useEffect, useId, useMemo, useState } from "react";

import { PlacedComponent } from "@/components/monograph/BundleView";
import { LegacyScope } from "@/components/monograph/LegacyScope";
import { useMonographSlot } from "@/components/monograph/MonographSlotContext";
import { useMotionAllowed } from "@/components/motion/useMotionAllowed";
import { generatorSpecShape, parseToolSpec, type GeneratorSection, type GeneratorSpec } from "@/lib/componentSpecsTools";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { nodeElements } from "@/lib/monographRenderElements";

export const REPLAY_STEP_MS = 900;
export const MEDIA_RAIL_LABEL = "Media for this answer";

export function writingLine(written: number, total: number): string {
  return `Writing section ${Math.min(written + 1, total)} of ${total}`;
}

function Section({ section, status, written, illustrate, renderUnit }: { section: GeneratorSection; status: string; written: boolean; illustrate: boolean; renderUnit: ComponentViewProps["renderUnit"] }) {
  const { sources } = useMonographSlot();
  return (
    <article className="gsec" data-n={section.number} data-state={written ? "done" : "queued"}>
      <div className="gsec-h">
        <span className="gsec-n">{section.number}</span>
        <h3 className="gsec-t">{section.titleUnit ? renderUnit(section.titleUnit) : section.title}</h3>
        <span className="gsec-k">{section.kind}</span>
        {written ? <span className="gsec-st">{status}</span> : null}
      </div>
      <div className={section.split ? "gsec-body split" : "gsec-body"} hidden={!written}>
        <div className="gsec-col">
          <p className="gsec-text">{section.textUnit ? renderUnit(section.textUnit) : nodeElements(section.text ?? [], sources)}</p>
        </div>
        {section.media.length ? (
          <div className={section.media.length > 1 ? "gsec-media two" : "gsec-media"} hidden={!illustrate}>
            {section.media.map((label) => (
              <PlacedComponent key={label} label={label} />
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function useReplay(total: number): { written: number; replay: () => void } {
  const motion = useMotionAllowed();
  const [written, setWritten] = useState(total);
  useEffect(() => {
    if (written >= total) return;
    const timer = window.setTimeout(() => setWritten((count) => count + 1), REPLAY_STEP_MS);
    return () => window.clearTimeout(timer);
  }, [written, total]);
  return { written, replay: () => setWritten(motion ? 0 : total) };
}

function MediaRail({ generator, renderUnit }: { generator: GeneratorSpec; renderUnit: ComponentViewProps["renderUnit"] }) {
  return (
    <div className="gen-side">
      <aside className="media-rail ai-only" aria-label={MEDIA_RAIL_LABEL}>
        <p className="kicker">{renderUnit(generator.railTitle)}</p>
        <p className="font-ui text-label text-ink-2">{renderUnit(generator.railDetail)}</p>
        <ul className="jobs">
          {generator.jobs.map((job) => (
            <li key={job.title}>
              <span>
                <span className="jt">{job.title}</span>
                <span className="js">{job.state}</span>
              </span>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}

type StripProps = { generator: GeneratorSpec; written: number; illustrate: boolean; onIllustrate: () => void; onReplay: () => void };

function GeneratorStrip({ generator, written, illustrate, onIllustrate, onReplay }: StripProps) {
  const switchId = useId();
  const total = generator.sections.length;
  const resting = written >= total;
  return (
    <div className="gen-strip">
      <div className="wrap">
        <div>
          <p className="gen-state" role="status">
            {resting ? generator.stage.state : writingLine(written, total)}
            <span className="gen-sub">{generator.stage.detail}</span>
          </p>
          <div className="gen-bar" aria-hidden="true">
            {generator.sections.map((section) => (
              <i key={section.number} className={section.number <= written ? "done" : undefined} />
            ))}
          </div>
        </div>
        <div className="gen-tools">
          <div className="switch-row">
            <span className="sw-text">
              <span className="sw-label" id={switchId}>
                {generator.switchLabel}
              </span>
              <span className="sw-desc">{generator.switchDetail}</span>
            </span>
            <button className="switch" type="button" role="switch" aria-checked={illustrate} aria-labelledby={switchId} onClick={onIllustrate} />
          </div>
          <div className="actions" data-count="1">
            <button className="btn sm" type="button" onClick={onReplay} disabled={!resting}>
              {generator.replay}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function GeneratorView({ spec, renderUnit }: ComponentViewProps) {
  const generator = useMemo(() => parseToolSpec(generatorSpecShape, spec), [spec]);
  const total = generator.sections.length;
  const { written, replay } = useReplay(total);
  const [illustrate, setIllustrate] = useState(true);
  const resting = written >= total;
  return (
    <LegacyScope scope="rm">
      <GeneratorStrip generator={generator} written={written} illustrate={illustrate} onIllustrate={() => setIllustrate((on) => !on)} onReplay={replay} />
      <div className="wrap">
        <div className="gen-wrap">
          <div className="gen-grid">
            <div className="gen-secs">
              {generator.sections.map((section) => (
                <Section key={section.number} section={section} status={generator.status} written={section.number <= written} illustrate={illustrate} renderUnit={renderUnit} />
              ))}
              {generator.film ? <div hidden={!illustrate || !resting}><PlacedComponent label={generator.film} /></div> : null}
            </div>
            <MediaRail generator={generator} renderUnit={renderUnit} />
          </div>
        </div>
      </div>
    </LegacyScope>
  );
}
