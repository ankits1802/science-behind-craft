import type { ReactNode } from "react";

import { kitMotionClass } from "@/lib/artKitMotion";
import { isKitScene, sceneMotion, type KitScene } from "@/lib/componentSpecsKitScene";

import { partIds, type KitIds } from "./kitIds";
import { KitKey } from "./KitKey";
import { PANEL_BOXES, PlacedPart } from "./KitPartArt";
import { KitTextures } from "./KitTextures";
import { WELL } from "./surfaces";

import "./artkit.css";

type RenderUnit = (ref: string) => ReactNode;
type SceneArtProps = { scene: KitScene; ids: KitIds; name: string; className?: string; seal?: boolean };

const FRAME = "0 0 240 160";
const SEAL_FRAME = "40 0 160 160";

export function KitSceneArt({ scene, ids, name, className, seal = false }: SceneArtProps) {
  const moving = sceneMotion(scene);
  const boxes = PANEL_BOXES[scene.parts.length];
  return (
    <svg
      className={className ? `kv-kit-scene ${className}` : "kv-kit-scene"}
      viewBox={seal && scene.parts.length === 1 ? SEAL_FRAME : FRAME}
      aria-hidden="true"
      focusable="false"
      data-kit-scene={name}
    >
      {seal ? null : <rect x="-240" y="-160" width="720" height="480" fill={WELL} />}
      {scene.parts.map((part, at) => (
        <PlacedPart
          key={`${part.part}-${at}`}
          part={part}
          ids={partIds(ids, `${name}-${at}`)}
          box={boxes[at]}
          moving={moving?.part === at ? { className: kitMotionClass(moving.motion), panel: 0 } : undefined}
        />
      ))}
    </svg>
  );
}

export function KitSceneKey({ scene, ids, renderUnit, className }: { scene: KitScene; ids: KitIds; renderUnit: RenderUnit; className?: string }) {
  return (
    <div className={className ? `kv-kit-scene-key ${className}` : "kv-kit-scene-key"}>
      <KitKey parts={scene.parts} ids={ids} renderUnit={renderUnit} />
    </div>
  );
}

export function KitSceneTextures({ ids, scenes }: { ids: KitIds; scenes: readonly unknown[] }) {
  return scenes.some(isKitScene) ? <KitTextures ids={ids} /> : null;
}
