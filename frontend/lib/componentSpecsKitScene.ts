import { ART_KIT, type KitMotion } from "@/lib/artKit";
import { kitPartShape, movingPart, speciesParts, type KitPart } from "@/lib/componentSpecsKit";
import { list, nullable, object, oneOf, optional, ShapeError, type Shape } from "@/lib/shape";

export const KIT_SCENE_KINDS = ["reaction_player", "dip_player", "stage_player", "choice_toggle", "label_card"] as const;

export type KitScene = { parts: KitPart[]; motion?: KitMotion | null };

const fields = object<KitScene>({ parts: list(kitPartShape, 1), motion: optional(nullable(oneOf(ART_KIT.motions))) });

export const kitSceneShape: Shape<KitScene> = {
  expected: "a kit scene of one to three named parts, or the species of one reaction",
  parse(value, path) {
    const scene = fields.parse(value, path);
    const most = speciesParts(scene.parts) ? ART_KIT.speciesPerSceneMax : ART_KIT.partsPerPanelMax;
    if (scene.parts.length > most) throw new ShapeError(`${path}.parts`, `at most ${most} parts`);
    return scene;
  }
};

const stillShape: Shape<KitScene> = {
  expected: "a kit scene at rest",
  parse(value, path) {
    const scene = kitSceneShape.parse(value, path);
    if (scene.motion) throw new ShapeError(`${path}.motion`, "no motion, since this scene rests as drawn");
    return scene;
  }
};

export function isKitScene(value: unknown): value is KitScene {
  return typeof value === "object" && value !== null && !Array.isArray(value) && "parts" in value;
}

function slot<T>(drawn: Shape<T>, kit: Shape<KitScene>): Shape<T | KitScene> {
  return {
    expected: `${drawn.expected} or ${kit.expected}`,
    parse: (value, path) => (isKitScene(value) ? kit.parse(value, path) : drawn.parse(value, path))
  };
}

export function sceneOr<T>(drawn: Shape<T>): Shape<T | KitScene> {
  return slot(drawn, kitSceneShape);
}

export function stillOr<T>(drawn: Shape<T>): Shape<T | KitScene> {
  return slot(drawn, stillShape);
}

export function sceneMotion(scene: KitScene): { part: number; motion: KitMotion } | null {
  const part = movingPart(scene);
  return part === null || !scene.motion ? null : { part, motion: scene.motion };
}
