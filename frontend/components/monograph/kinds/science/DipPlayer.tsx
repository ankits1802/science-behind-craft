import type { ComponentViewProps } from "@/lib/componentViewContract";
import { dipPlayerShape } from "@/lib/componentSpecsSciencePlayers";
import { parseShape } from "@/lib/shape";

import { EquationView } from "./parts/Chemistry";
import { Drawing } from "./parts/Drawing";
import { swatchStyle } from "./parts/props";
import { FigureHeadLines } from "./parts/Text";

export function DipPlayer({ spec, renderUnit }: ComponentViewProps) {
  const player = parseShape(dipPlayerShape, spec);
  const lastPhase = player.phases.length - 1;
  const lastDip = player.dips.length - 1;
  return (
    <figure className="vat" id={player.id} data-dips={player.dips.length} data-pose={player.phases[lastPhase].pose} aria-labelledby={player.head.titleId ?? undefined}>
      <figcaption className="vat-head">
        <FigureHeadLines head={player.head} renderUnit={renderUnit} />
      </figcaption>
      <div className="vat-scene">
        <p className="vat-phase" aria-hidden="true">
          {renderUnit(player.phase)}
        </p>
        <Drawing node={player.scene} />
      </div>
      <ol className="vat-strip" aria-label={player.stripLabel}>
        {player.phases.map((phase, index) => (
          <li key={phase.pose} className="vs" data-pose={phase.pose} aria-current={index === lastPhase ? "step" : undefined}>
            <Drawing node={phase.drawing} />
            <p className="vs-k">{renderUnit(phase.kicker)}</p>
            <p className="vs-t">{renderUnit(phase.text)}</p>
          </li>
        ))}
      </ol>
      <div className="vat-ctl">
        <button className="btn vat-dip" type="button">
          {player.dipAgain}
        </button>
        <p className="vat-status" role="status" aria-live="polite">
          {renderUnit(player.status)}
        </p>
        <div className="dips">
          <p className="dips-l">{renderUnit(player.dipsLabel)}</p>
          <ol>
            {player.dips.map((colour, index) => (
              <li key={colour} data-n={index + 1} className={index === lastDip ? "on" : undefined}>
                <span className="dsw" style={swatchStyle(colour)} aria-hidden="true" />
                <span>{index + 1}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
      <EquationView equation={player.equation} renderUnit={renderUnit} />
    </figure>
  );
}
