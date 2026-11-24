import { KitSceneArt, KitSceneKey, KitSceneTextures } from "@/components/artkit/KitScene";
import { kitIds, type KitIds } from "@/components/artkit/kitIds";
import { isKitScene } from "@/lib/componentSpecsKitScene";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { reactionPlayerShape, type ReactionPlayerSpec, type StepScene } from "@/lib/componentSpecsSciencePlayers";
import { parseShape } from "@/lib/shape";

import { Drawing, Drawings } from "./parts/Drawing";
import { PlayIcon } from "./parts/icons";
import { FigureHeadLines, type RenderUnit } from "./parts/Text";
import { ChemistryPartView } from "./ReactionChemistry";
import { ReactionStepText } from "./ReactionStepText";

function Rail({ player }: { player: ReactionPlayerSpec }) {
  return (
    <div className="rp-bar">
      <div className="rp-rail" role="group" aria-label="Steps">
        {player.steps.map((step, index) => {
          const pressed = index + 1 === player.current;
          return (
            <button key={step.name} type="button" aria-pressed={pressed} tabIndex={pressed ? 0 : -1} aria-label={`${index + 1} ${step.name}`}>
              <b>{index + 1}</b> <span aria-hidden="true">{step.name}</span>
            </button>
          );
        })}
      </div>
      <button className="btn sm rp-play" type="button" aria-pressed="false">
        <PlayIcon />
        <span>Play</span>
      </button>
    </div>
  );
}

type ReactionProps = { scene: StepScene; step: number; shown: boolean; ids: KitIds; renderUnit: RenderUnit };

function Reaction({ scene, step, shown, ids, renderUnit }: ReactionProps) {
  const art = scene.art;
  return (
    <div className="rx" data-i={step} hidden={!shown}>
      <div className="rx-where">
        {scene.whereIcon ? <Drawing node={scene.whereIcon} /> : null}
        <p>{renderUnit(scene.where)}</p>
      </div>
      <div className="rx-art">{isKitScene(art) ? <KitSceneArt scene={art} ids={ids} name={`r${step}`} /> : <Drawings nodes={art} />}</div>
      {isKitScene(art) ? <KitSceneKey scene={art} ids={ids} renderUnit={renderUnit} /> : null}
    </div>
  );
}

function Scene({ player, ids, renderUnit }: { player: ReactionPlayerSpec; ids: KitIds; renderUnit: RenderUnit }) {
  return (
    <div className="rp-scene">
      <Drawings nodes={player.scenes} />
      {player.steps.map((step, index) =>
        step.scene ? <Reaction key={step.name} scene={step.scene} step={index + 1} shown={index + 1 === player.current} ids={ids} renderUnit={renderUnit} /> : null
      )}
      {player.key !== null ? (
        <p className="rx-key">
          <span className="rk" aria-hidden="true" />
          {player.key}
        </p>
      ) : null}
      <p className="rp-status" role="status" aria-live="polite">
        {renderUnit(player.status)}
      </p>
    </div>
  );
}

export function ReactionPlayer({ component, spec, renderUnit }: ComponentViewProps) {
  const player = parseShape(reactionPlayerShape, spec);
  const reacting = player.steps.some((step) => step.scene !== null);
  const ids = kitIds(component.label);
  return (
    <figure className={reacting ? "rp rx-player" : "rp"} id={player.id} data-track={player.track} data-step={player.current} data-steps={player.steps.length}>
      <figcaption className="rp-cap">
        <FigureHeadLines head={player.head} renderUnit={renderUnit} />
      </figcaption>
      <Rail player={player} />
      <div className="rp-body">
        <Scene player={player} ids={ids} renderUnit={renderUnit} />
        <div className="rp-text">
          {player.steps.map((step, index) => (
            <ReactionStepText key={step.name} text={step.text} step={index + 1} shown={index + 1 === player.current} renderUnit={renderUnit} />
          ))}
        </div>
      </div>
      <div className="rp-chems">
        {player.steps.map((step, index) => (
          <div key={step.name} className="rp-chem" hidden={index + 1 !== player.current}>
            {step.chemistry.parts.map((part, at) => <ChemistryPartView key={at} part={part} renderUnit={renderUnit} />)}
          </div>
        ))}
      </div>
      <KitSceneTextures ids={ids} scenes={player.steps.map((step) => step.scene?.art)} />
    </figure>
  );
}
