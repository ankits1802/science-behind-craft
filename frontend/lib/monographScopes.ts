export type KitScope = "mb" | "chem" | "pt" | "rm" | "sa" | "ask";

export type KitFrame = "bare" | "screen" | "wrap" | "column";

export type ComponentPlace = { scope: KitScope; frame: KitFrame };

const PLACES: Readonly<Record<string, ComponentPlace>> = {
  ask_next: { scope: "rm", frame: "wrap" },
  audio_player: { scope: "rm", frame: "wrap" },
  chart: { scope: "mb", frame: "wrap" },
  citation_tool: { scope: "rm", frame: "bare" },
  comic: { scope: "sa", frame: "bare" },
  concept_atlas: { scope: "mb", frame: "wrap" },
  credits: { scope: "pt", frame: "screen" },
  diagram: { scope: "mb", frame: "wrap" },
  dip_player: { scope: "chem", frame: "wrap" },
  equation_card: { scope: "chem", frame: "wrap" },
  experiment_lab: { scope: "pt", frame: "wrap" },
  explainer: { scope: "mb", frame: "screen" },
  fact_table: { scope: "mb", frame: "wrap" },
  generator: { scope: "rm", frame: "bare" },
  label_card: { scope: "pt", frame: "wrap" },
  language_switch: { scope: "rm", frame: "wrap" },
  map_layer: { scope: "pt", frame: "wrap" },
  map_sequence: { scope: "pt", frame: "wrap" },
  material_cards: { scope: "chem", frame: "wrap" },
  model_explainer: { scope: "chem", frame: "wrap" },
  molecule_3d: { scope: "chem", frame: "wrap" },
  picture_plate: { scope: "pt", frame: "column" },
  process_replay: { scope: "ask", frame: "screen" },
  quiz: { scope: "rm", frame: "wrap" },
  reaction_player: { scope: "chem", frame: "wrap" },
  reading_level: { scope: "sa", frame: "bare" },
  related_crafts: { scope: "rm", frame: "wrap" },
  source_disagreements: { scope: "chem", frame: "wrap" },
  source_list: { scope: "rm", frame: "wrap" },
  specimen_plate: { scope: "mb", frame: "screen" },
  stage_player: { scope: "pt", frame: "wrap" },
  structure_diagram: { scope: "rm", frame: "wrap" },
  swatch_cards: { scope: "mb", frame: "screen" },
  timeline_map: { scope: "pt", frame: "wrap" },
  voice: { scope: "mb", frame: "bare" }
};

const UNKNOWN_PLACE: ComponentPlace = { scope: "mb", frame: "wrap" };

export function componentPlace(kind: string | null): ComponentPlace {
  return kind !== null && Object.hasOwn(PLACES, kind) ? PLACES[kind] : UNKNOWN_PLACE;
}
