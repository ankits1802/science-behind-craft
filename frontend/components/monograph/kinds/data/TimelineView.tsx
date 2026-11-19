import { timelineShape } from "@/lib/componentSpecsData";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

export function TimelineView({ spec, renderUnit }: ComponentViewProps) {
  const ladder = parseShape(timelineShape, spec);
  const variant = ladder.variant;
  const scale = ladder.scale;
  return (
    <div className={`${variant}-ladder`}>
      <p className="fig-no" data-fig={ladder.number.ref}>
        {renderUnit(ladder.number.unit)}
      </p>
      <p className={`chart-title ${variant}-t`}>{renderUnit(ladder.title)}</p>
      <div className={`${variant}-scale`} role="img" aria-label={scale.label}>
        <span className="gl"></span>
        {scale.marks.map((mark) => (
          <span key={mark.left} className={mark.final ? "gd fin" : "gd"} style={{ left: mark.left }}></span>
        ))}
        {scale.spans.map((span) => (
          <span key={span.left} className="gspan" style={{ left: span.left }}>
            {span.text}
          </span>
        ))}
        {scale.ticks.map((tick) => (
          <span key={tick.left} className={`gx ${tick.side}`} style={{ left: tick.left }}>
            {tick.text}
          </span>
        ))}
      </div>
      <ol className={`${variant}-steps`}>
        {ladder.steps.map((step) => (
          <li key={step}>{renderUnit(step)}</li>
        ))}
      </ol>
    </div>
  );
}
