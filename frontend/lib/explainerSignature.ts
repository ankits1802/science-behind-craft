import { UUID } from "@/lib/answerShapes";
import { envelope, explainerSentenceShape, type BlockEnvelope, type ExplainerSentence } from "@/lib/explainerBlockBase";
import { boolean, integer, list, nullable, object, oneOf, text, type Shape } from "@/lib/shape";

export const SIGNATURE_KINDS = ["indigo_vat", "mordant_bath", "lost_wax", "firing"] as const;
export const VAT_KINDS = ["FERMENTED", "CHEMICAL"] as const;
export const INDIGO_FORMS = ["KETO", "LEUCO"] as const;
export const LOST_WAX_STEPS = ["MODEL", "JACKET", "BURNOUT", "POUR", "BREAK_OUT"] as const;
export const FIRING_ATMOSPHERES = ["OXIDISING", "REDUCING"] as const;

export type SignatureKind = (typeof SIGNATURE_KINDS)[number];
export type CompoundRef = { compoundId: string; pubchemCid: number; formula: string | null; sourceId: string };
export type IndigoForm = {
  form: (typeof INDIGO_FORMS)[number];
  name: string;
  colour: string;
  soluble: boolean;
  compound: CompoundRef | null;
  sentence: ExplainerSentence;
};
export type VatDip = { dips: number; stated: string; shade: string | null; sentence: ExplainerSentence };
export type VatContent = { name: string; sentence: ExplainerSentence };
export type IndigoVatBlock = BlockEnvelope<"indigo_vat"> & {
  vat: (typeof VAT_KINDS)[number];
  lift: ExplainerSentence;
  forms: IndigoForm[];
  dips: VatDip[];
  contents: VatContent[];
};
export type MordantSwatch = { mordant: string | null; colour: string; sentence: ExplainerSentence };
export type MordantBathBlock = BlockEnvelope<"mordant_bath"> & { dye: string; fibre: string; swatches: MordantSwatch[] };
export type LostWaxStep = { step: (typeof LOST_WAX_STEPS)[number]; sentence: ExplainerSentence };
export type LostWaxBlock = BlockEnvelope<"lost_wax"> & { metal: string; steps: LostWaxStep[] };
export type FiringAtmosphere = { atmosphere: (typeof FIRING_ATMOSPHERES)[number]; colour: string; sentence: ExplainerSentence };
export type FiringTemperature = { stated: string; sentence: ExplainerSentence };
export type FiringBlock = BlockEnvelope<"firing"> & { body: string; atmospheres: FiringAtmosphere[]; temperature: FiringTemperature | null };
export type SignatureBlock = IndigoVatBlock | MordantBathBlock | LostWaxBlock | FiringBlock;

const compoundRefShape = object<CompoundRef>({ compoundId: UUID, pubchemCid: integer, formula: nullable(text), sourceId: text });

export const indigoVatBlockShape: Shape<IndigoVatBlock> = object<IndigoVatBlock>({
  ...envelope("indigo_vat"),
  vat: oneOf(VAT_KINDS),
  lift: explainerSentenceShape,
  forms: list(
    object<IndigoForm>({
      form: oneOf(INDIGO_FORMS),
      name: text,
      colour: text,
      soluble: boolean,
      compound: nullable(compoundRefShape),
      sentence: explainerSentenceShape
    })
  ),
  dips: list(object<VatDip>({ dips: integer, stated: text, shade: nullable(text), sentence: explainerSentenceShape })),
  contents: list(object<VatContent>({ name: text, sentence: explainerSentenceShape }))
});

export const mordantBathBlockShape: Shape<MordantBathBlock> = object<MordantBathBlock>({
  ...envelope("mordant_bath"),
  dye: text,
  fibre: text,
  swatches: list(object<MordantSwatch>({ mordant: nullable(text), colour: text, sentence: explainerSentenceShape }), 1)
});

export const lostWaxBlockShape: Shape<LostWaxBlock> = object<LostWaxBlock>({
  ...envelope("lost_wax"),
  metal: text,
  steps: list(object<LostWaxStep>({ step: oneOf(LOST_WAX_STEPS), sentence: explainerSentenceShape }), 1)
});

export const firingBlockShape: Shape<FiringBlock> = object<FiringBlock>({
  ...envelope("firing"),
  body: text,
  atmospheres: list(object<FiringAtmosphere>({ atmosphere: oneOf(FIRING_ATMOSPHERES), colour: text, sentence: explainerSentenceShape }), 1),
  temperature: nullable(object<FiringTemperature>({ stated: text, sentence: explainerSentenceShape }))
});

export function signatureSentences(block: SignatureBlock): ExplainerSentence[] {
  if (block.kind === "indigo_vat") return [block.lift, ...block.forms.map((form) => form.sentence), ...block.dips.map((dip) => dip.sentence), ...block.contents.map((content) => content.sentence)];
  if (block.kind === "mordant_bath") return block.swatches.map((swatch) => swatch.sentence);
  if (block.kind === "lost_wax") return block.steps.map((step) => step.sentence);
  return [...block.atmospheres.map((atmosphere) => atmosphere.sentence), ...(block.temperature ? [block.temperature.sentence] : [])];
}

export function signatureSourceIds(block: SignatureBlock): string[] {
  return block.kind === "indigo_vat" ? block.forms.flatMap((form) => (form.compound ? [form.compound.sourceId] : [])) : [];
}
