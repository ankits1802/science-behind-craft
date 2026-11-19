import { citationToolShape, type CitePanel } from "@/lib/componentSpecsData";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

function PanelView({ panel, shown, renderUnit }: { panel: CitePanel; shown: boolean; renderUnit: ComponentViewProps["renderUnit"] }) {
  const texts = Object.fromEntries(panel.styles.map((style) => [`data-${style.value}`, style.text]));
  return (
    <div className="kv-cp" id={panel.panelId} role="tabpanel" aria-labelledby={panel.tabId} hidden={!shown}>
      <div className={panel.box.join(" ")}>
        <section className="screen" data-aid={panel.aid}>
          <div className={panel.cites.join(" ")}>
            <div className="cite-box" id={panel.boxId ?? undefined}>
              <div className="seg cb-seg" role="group" aria-label="Citation style">
                {panel.styles.map((style, index) => (
                  <button key={style.value} type="button" aria-pressed={index === 0 ? "true" : "false"} {...{ [`data-${panel.styleKey}`]: style.value }}>
                    {style.label}
                  </button>
                ))}
              </div>
              <p className="cb-text" id={panel.textId} {...texts}>
                {renderUnit(panel.text)}
              </p>
              <p className="cb-link">{renderUnit(panel.link)}</p>
              <div className="actions" data-count="1">
                <button className="btn sm" type="button" data-copy={panel.textId}>
                  {panel.copyLabel}
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export function CitationToolView({ spec, renderUnit }: ComponentViewProps) {
  const tool = parseShape(citationToolShape, spec);
  return (
    <section className="kv-cite" id="kv-cite" aria-labelledby={tool.titleId}>
      <div className="kv-cite-top">
        <h3 className="kv-sub-h" id={tool.titleId}>
          {renderUnit(tool.title)}
        </h3>
        <div className="kv-tabs" role="tablist" aria-label={tool.tabsLabel}>
          {tool.panels.map((panel, index) => (
            <button
              key={panel.key}
              type="button"
              role="tab"
              id={panel.tabId}
              aria-controls={panel.panelId}
              aria-selected={index === 0 ? "true" : "false"}
              tabIndex={index === 0 ? undefined : -1}
              data-kv-ct={panel.key}
            >
              {panel.label}
            </button>
          ))}
        </div>
      </div>
      {tool.panels.map((panel, index) => (
        <PanelView key={panel.key} panel={panel} shown={index === 0} renderUnit={renderUnit} />
      ))}
    </section>
  );
}
