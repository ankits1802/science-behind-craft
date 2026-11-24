import { KitSceneArt, KitSceneKey, KitSceneTextures } from "@/components/artkit/KitScene";
import { kitIds, type KitIds } from "@/components/artkit/kitIds";
import { isKitScene } from "@/lib/componentSpecsKitScene";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { dipPlayerShape, type DipPhase, type DipPlayerSpec } from "@/lib/componentSpecsSciencePlayers";
import { parseShape } from "@/lib/shape";

import { EquationView } from "./parts/Chemistry";
import { Drawing } from "./parts/Drawing";
import { swatchStyle } from "./parts/props";
import { FigureHeadLines, type RenderUnit } from "./parts/Text";

type PhaseProps = { phase: DipPhase; index: number; last: boolean; ids: KitIds; renderUnit: RenderUnit };

function Phase({ phase, index, last, ids, renderUnit }: PhaseProps) {
  const drawing = phase.drawing;
  return (
    <li className="vs" data-pose={phase.pose} aria-current={last ? "step" : undefined}>
      {isKitScene(drawing) ? <KitSceneArt scene={drawing} ids={ids} name={`ph${index}`} className="vf-mini" /> : <Drawing node={drawing} />}
      <p className="vs-k">{renderUnit(phase.kicker)}</p>
      <p className="vs-t">{renderUnit(phase.text)}</p>
      {isKitScene(drawing) ? <KitSceneKey scene={drawing} ids={ids} renderUnit={renderUnit} /> : null}
    </li>
  );
}

function Strip({ player, ids, renderUnit }: { player: DipPlayerSpec; ids: KitIds; renderUnit: RenderUnit }) {
  const last = player.phases.length - 1;
  return (
    <ol className="vat-strip" aria-label={player.stripLabel}>
      {player.phases.map((phase, index) => (
        <Phase key={phase.pose} phase={phase} index={index} last={index === last} ids={ids} renderUnit={renderUnit} />
      ))}
    </ol>
  );
}

function Controls({ player, renderUnit }: { player: DipPlayerSpec; renderUnit: RenderUnit }) {
  const last = player.dips.length - 1;
  return (
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
            <li key={colour} data-n={index + 1} className={index === last ? "on" : undefined}>
              <span className="dsw" style={swatchStyle(colour)} aria-hidden="true" />
              <span>{index + 1}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

export function DipPlayer({ component, spec, renderUnit }: ComponentViewProps) {
  const player = parseShape(dipPlayerShape, spec);
  const pose = player.phases[player.phases.length - 1].pose;
  const ids = kitIds(component.label);
  const scene = player.scene;
  return (
    <figure className="vat" id={player.id} data-dips={player.dips.length} data-pose={pose} aria-labelledby={player.head.titleId ?? undefined}>
      <figcaption className="vat-head">
        <FigureHeadLines head={player.head} renderUnit={renderUnit} />
      </figcaption>
      <div className="vat-scene">
        <p className="vat-phase" aria-hidden="true">
          {renderUnit(player.phase)}
        </p>
        {isKitScene(scene) ? <KitSceneArt scene={scene} ids={ids} name="scene" className="vat-svg" /> : <Drawing node={scene} />}
      </div>
      {isKitScene(scene) ? <KitSceneKey scene={scene} ids={ids} renderUnit={renderUnit} className="vat-key" /> : null}
      <Strip player={player} ids={ids} renderUnit={renderUnit} />
      <Controls player={player} renderUnit={renderUnit} />
      {player.equation ? <EquationView equation={player.equation} renderUnit={renderUnit} /> : null}
      <KitSceneTextures ids={ids} scenes={[scene, ...player.phases.map((phase) => phase.drawing)]} />
    </figure>
  );
}
