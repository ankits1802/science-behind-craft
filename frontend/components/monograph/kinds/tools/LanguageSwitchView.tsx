"use client";

import { useMemo, useState } from "react";

import { Plate } from "@/components/editorial/Plate";
import { PlacedComponent } from "@/components/monograph/BundleView";
import { LegacyScope } from "@/components/monograph/LegacyScope";
import { useMonographSlot } from "@/components/monograph/MonographSlotContext";
import { languageSwitchSpecShape, parseToolSpec, type LanguagePanel, type PanelProvenance } from "@/lib/componentSpecsTools";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { nodeElements } from "@/lib/monographRenderElements";

const NARROW_SPACE = "\u202f";
export const PANEL_NOTES_LABEL = "Sources in this passage";

function Provenance({ provenance }: { provenance: PanelProvenance }) {
  return (
    <p className="rail provenance">
      {provenance.items.map((item) => (
        <span key={item}>{item}</span>
      ))}
      <span className="rel-strip" role="img" aria-label={provenance.reliability.label}>
        {provenance.reliability.grades.map((found) => (
          <span className="rs-g" key={found.grade}>
            <span className={`rel ${found.grade}`} aria-hidden="true" />
            {`${found.grade}${NARROW_SPACE}${found.count}`}
          </span>
        ))}
      </span>
      <a href={provenance.monograph.href}>{provenance.monograph.text}</a>
      <span>{provenance.answered}</span>
      <button className="listen-open" type="button" data-listen-open="" aria-controls="kv-player">
        <svg viewBox="0 0 16 16" aria-hidden="true">
          <path d="M4.5 2.8 L13 8 L4.5 13.2 Z" fill="currentColor" />
        </svg>
        <span>{`${provenance.listen.label} ${provenance.listen.minutes} ${provenance.listen.unit}`}</span>
      </button>
    </p>
  );
}

function Panel({ panel, shown, renderUnit }: { panel: LanguagePanel; shown: boolean; renderUnit: ComponentViewProps["renderUnit"] }) {
  const { sources } = useMonographSlot();
  return (
    <div className="lang-panel" data-ui-lang={panel.lang} lang={panel.lang} dir={panel.direction} hidden={!shown}>
      <div className="spread railed">
        <Provenance provenance={panel.provenance} />
      </div>
      <div className="spread railed direct">
        <div className="rail" />
        <div className={`main ${panel.lang}-prose`}>
          <p className="t-lede">{nodeElements(panel.lede, sources)}</p>
          <div className="actions direct-actions start" data-count="2">
            <button className="btn sm" type="button" data-save="" aria-pressed="false">
              {panel.actions.save}
            </button>
            <button className="btn sm" type="button" data-kv-goto="kv-cite">
              {panel.actions.cite}
            </button>
          </div>
          <span className="sec-kind mt-12">{panel.section.kind}</span>
          <h2 className="t-h2 mb-4">{renderUnit(panel.section.title)}</h2>
          <p>{nodeElements(panel.section.body, sources)}</p>
          {panel.figure ? <PlacedComponent label={panel.figure} /> : null}
        </div>
        <aside className="margin note keep" aria-label={PANEL_NOTES_LABEL}>
          <ul>
            {panel.notes.map((ref) => (
              <li key={ref}>{renderUnit(ref)}</li>
            ))}
          </ul>
          {panel.plate ? (
            <div className="margin-plate">
              <Plate
                src={panel.plate.src}
                alt={panel.plate.alt}
                ratio={`${panel.plate.width} / ${panel.plate.height}`}
                caption={<span className={`${panel.lang}-prose not-italic`}>{nodeElements(panel.plate.caption, sources)}</span>}
                credit={renderUnit(panel.plate.credit)}
              />
            </div>
          ) : null}
        </aside>
      </div>
    </div>
  );
}

export function LanguageSwitchView({ spec, renderUnit }: ComponentViewProps) {
  const languages = useMemo(() => parseToolSpec(languageSwitchSpecShape, spec), [spec]);
  const [lang, setLang] = useState(languages.options[0].lang);
  const status = languages.options.find((option) => option.lang === lang)?.status;
  return (
    <LegacyScope scope="rm">
      <div className="lang-demo">
        <div className="lang-bar">
          <span className="t-label text-ink-3">{languages.label}</span>
          <div className="seg" role="group" aria-label={languages.label}>
            {languages.options.map((option) => (
              <button key={option.lang} type="button" aria-pressed={option.lang === lang} lang={option.lang} onClick={() => setLang(option.lang)}>
                <span dir={option.direction}>{option.name}</span>
              </button>
            ))}
          </div>
          <span className="t-caption" role="status">
            {status}
          </span>
        </div>
        <div className="lang-panels">
          <div className="lang-panel" data-ui-lang={languages.options[0].lang} lang={languages.options[0].lang} hidden={lang !== languages.options[0].lang}>
            <p className="kv-lang-en">{renderUnit(languages.english)}</p>
          </div>
          {languages.panels.map((panel) => (
            <Panel key={panel.lang} panel={panel} shown={panel.lang === lang} renderUnit={renderUnit} />
          ))}
        </div>
      </div>
    </LegacyScope>
  );
}
