import { ART_KIT, FAMILY_NAMES, KIT_MATERIALS, KIT_PART_NAMES, materialName, type KitPartName } from "@/lib/artKit";
import type { KitDiagramSpec, KitPart } from "@/lib/componentSpecsKit";

export type SheetTile = { key: string; caption: string; part: KitPart };
export type SheetPart = { name: KitPartName; title: string; families: string; variants: SheetTile[]; materials: SheetTile[] };
export type SheetLayout = { key: string; title: string; spec: KitDiagramSpec; texts: Readonly<Record<string, string>> };

const LABEL = "u0001";

export const PART_TITLES: Readonly<Record<KitPartName, string>> = {
  cloth: "Cloth",
  block: "A carved block and its print",
  bath: "A vat or bath with its liquor",
  paste: "A paste or mordant applied",
  heat: "Heat or sun",
  water: "Water and washing",
  tool: "A tool in a hand",
  section: "A layered section",
  piece: "A shaped piece"
};

const MATERIAL_TILE: Readonly<Record<KitPartName, ((token: string) => KitPart) | null>> = {
  cloth: (token) => ({ part: "cloth", form: "swatch", material: token, label: LABEL }),
  block: (token) => ({ part: "block", motif: "star", paste: token, label: LABEL }),
  bath: (token) => ({ part: "bath", vessel: "vat", liquor: token, label: LABEL }),
  paste: (token) => ({ part: "paste", form: "spread", material: token, label: LABEL }),
  heat: null,
  water: null,
  tool: (token) => ({ part: "tool", tool: "brush", load: token, label: LABEL }),
  section: (token) => ({ part: "section", layers: [{ material: ART_KIT.earth, label: LABEL }, { material: token, label: LABEL }], label: LABEL }),
  piece: (token) => ({ part: "piece", shape: "lump", material: token, label: LABEL })
};

const tile = (key: string, caption: string, part: KitPart): SheetTile => ({ key, caption, part });

const VARIANTS: Readonly<Record<KitPartName, () => SheetTile[]>> = {
  cloth: () => [
    ...ART_KIT.parts.cloth.choices.form.map((form) => tile(form, form, { part: "cloth", form, material: "--dye-indigo", printed: { motif: "star", material: "--dye-lime" }, label: LABEL })),
    ...ART_KIT.motifs.map((motif) => tile(`printed-${motif}`, `printed, ${motif}`, { part: "cloth", form: "swatch", material: "--dye-cloth", printed: { motif, material: "--dye-madder" }, label: LABEL }))
  ],
  block: () => [...ART_KIT.motifs.map((motif) => tile(motif, motif, { part: "block", motif, paste: "--dye-kut", label: LABEL })), tile("uninked", "uninked", { part: "block", motif: "star", label: LABEL })],
  bath: () => [
    ...ART_KIT.parts.bath.choices.vessel.map((vessel) => tile(vessel, vessel, { part: "bath", vessel, liquor: "--dye-vat-liquor", piece: "--dye-leuco", label: LABEL })),
    tile("unstated-liquor", "liquor unstated", { part: "bath", vessel: "pot", piece: "--dye-bidri-black", label: LABEL })
  ],
  paste: () => [
    ...ART_KIT.parts.paste.choices.form.map((form) => tile(form, form, { part: "paste", form, material: "--dye-mud", on: "--dye-cloth", label: LABEL })),
    tile("dried", "dried", { part: "paste", form: "spread", material: "--dye-mud-wet", dried: "--dye-mud", on: "--dye-harda", label: LABEL })
  ],
  heat: () => ART_KIT.parts.heat.choices.source.map((source) => tile(source, source, { part: "heat", source, label: LABEL })),
  water: () => ART_KIT.parts.water.choices.form.map((form) => tile(form, form, { part: "water", form, label: LABEL })),
  tool: () => [...ART_KIT.parts.tool.choices.tool.map((name) => tile(name, name, { part: "tool", tool: name, load: name === "brush" || name === "stick" ? "--dye-madder" : null, label: LABEL })), tile("not-held", "not held", { part: "tool", tool: "chisel", held: false, label: LABEL })],
  section: () =>
    [2, 3, 4, 5, 6].map((count) =>
      tile(`layers-${count}`, `${count} layers`, { part: "section", layers: ["earth", "--dye-mud", "--dye-lime", "--dye-cloth", "--dye-indigo", "--dye-kut"].slice(0, count).map((material) => ({ material, label: LABEL })), label: LABEL })
    ),
  piece: () => [...ART_KIT.parts.piece.choices.shape.map((shape) => tile(shape, shape, { part: "piece", shape, label: LABEL })), tile("inlaid", "inlaid", { part: "piece", shape: "vessel", material: "--dye-bidri-black", inlay: { motif: "lines", material: "--dye-bidri-silver" }, label: LABEL })]
};

function familyLine(name: KitPartName): string {
  const names = ART_KIT.parts[name].families.map((family) => FAMILY_NAMES[family]);
  return `Serves ${names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}` : names[0]}`;
}

export function kitSheet(): SheetPart[] {
  return KIT_PART_NAMES.map((name) => {
    const drawn = MATERIAL_TILE[name];
    return {
      name,
      title: PART_TITLES[name],
      families: familyLine(name),
      variants: VARIANTS[name](),
      materials: drawn ? KIT_MATERIALS.map((token) => tile(token, materialName(token), drawn(token))) : []
    };
  });
}

const cloth = (label: string, material: string): KitPart => ({ part: "cloth", form: "swatch", material, label });

export function kitSheetLayouts(): SheetLayout[] {
  const texts = { u0001: "The figure's title", u0002: "First", u0003: "Second", u0004: "Third", u0005: "A part's label", u0006: "changed", u0007: "What the figure shows, in words", u0008: "Top layer", u0009: "Middle layer", u0010: "Bottom layer" };
  const head = { title: "u0001" };
  return [
    { key: "steps", title: "A row of steps", texts, spec: { head, layout: "steps", alt: "u0007", panels: ["--dye-cloth", "--dye-harda", "--dye-indigo"].map((material, at) => ({ label: `u000${at + 2}`, parts: [cloth("u0005", material)] })) } },
    {
      key: "before_after",
      title: "Before and after",
      texts,
      spec: { head, layout: "before_after", alt: "u0007", panels: [{ label: "u0002", parts: [cloth("u0005", "--dye-cloth")] }, { label: "u0003", via: "u0006", motion: "take", parts: [cloth("u0005", "--dye-madder")] }] }
    },
    {
      key: "section",
      title: "A section",
      texts,
      spec: { head, layout: "section", alt: "u0007", panels: [{ label: "u0002", parts: [{ part: "section", label: "u0005", layers: [{ material: "earth", label: "u0008" }, { material: "--dye-mud", label: "u0009" }, { material: "--dye-cloth", label: "u0010" }] }] }] }
    },
    {
      key: "sequence",
      title: "A sequence with arrows",
      texts,
      spec: {
        head,
        layout: "sequence",
        alt: "u0007",
        panels: [
          { label: "u0002", parts: [cloth("u0005", "--dye-cloth")] },
          { label: "u0003", via: "u0006", motion: "dip", parts: [{ part: "bath", vessel: "vat", liquor: "--dye-vat-liquor", piece: "--dye-leuco", label: "u0005" }] },
          { label: "u0004", via: "u0006", parts: [cloth("u0005", "--dye-indigo"), { part: "heat", source: "sun", label: "u0005" }] }
        ]
      }
    }
  ];
}
