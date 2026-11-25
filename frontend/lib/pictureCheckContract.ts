import { INSTANT, UUID } from "@/lib/answerShapes";
import { mediaRefShape, type MediaRef } from "@/lib/explainerBlockBase";
import { boolean, list, nullable, object, oneOf, text, type Shape } from "@/lib/shape";

export const PICTURE_VERDICTS = ["SHOWS", "DOES_NOT_SHOW"] as const;
export const CHECK_STATES = ["SEEN", "WAITING", "HIDDEN", "IN_REVIEW"] as const;

export type PictureVerdict = (typeof PICTURE_VERDICTS)[number];
export type CheckState = (typeof CHECK_STATES)[number];

export type VerdictView = {
  verdict: PictureVerdict;
  reason: string | null;
  by: string | null;
  ruling: boolean;
  trusted: boolean;
  at: string;
};

export type PictureCheckReview = {
  media: MediaRef;
  factId: string;
  fact: string;
  state: CheckState;
  verdicts: VerdictView[];
};

const verdictShape: Shape<VerdictView> = object<VerdictView>({
  verdict: oneOf(PICTURE_VERDICTS),
  reason: nullable(text),
  by: nullable(text),
  ruling: boolean,
  trusted: boolean,
  at: INSTANT
});

export const pictureCheckShape: Shape<PictureCheckReview> = object<PictureCheckReview>({
  media: mediaRefShape,
  factId: UUID,
  fact: text,
  state: oneOf(CHECK_STATES),
  verdicts: list(verdictShape)
});
