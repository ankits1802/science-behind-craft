import { expect, test } from "@playwright/test";

import {
  canWithdraw,
  declarationBody,
  declarationProblems,
  fileProblem,
  IMAGE_TERMS_VERSION,
  imageContributionShape,
  type ImageContribution,
  type ImageDeclaration
} from "../lib/imageContributionContract";
import { ROUTE_GUARDS } from "../lib/permissions";
import { parseShape } from "../lib/shape";

const PHOTO: ImageDeclaration = {
  craftSlug: "Kutch-Ajrakh",
  stageId: null,
  claimIds: [],
  origin: "PHOTOGRAPH",
  generator: "left over from an earlier choice",
  prompt: "left over",
  caption: "A printer lifts the block",
  altText: "Hands lifting a carved wooden block from red cloth"
};

const VIEW: ImageContribution = {
  id: "8b2f1d8e-2c1b-4c55-9a33-6a7b1c2d3e4f",
  craftSlug: "Kutch-Ajrakh",
  craftName: "Kutch Ajrakh",
  stageId: null,
  claimIds: ["4d1c2b3a-0000-4000-8000-000000000001"],
  origin: "AI_GENERATED",
  label: "Illustration, made with ChatGPT, gpt-image-1",
  generator: "ChatGPT, gpt-image-1",
  prompt: "An indigo vat",
  caption: "The vat turns yellow-green",
  altText: "A clay vat",
  status: "PENDING",
  aiMarked: true,
  mime: "image/png",
  width: 800,
  height: 600,
  fileUrl: "https://bucket.example/media/x.png",
  createdAt: "2026-11-19T10:00:00Z",
  reviewedAt: null,
  reviewNote: null
};

test("an AI-made picture names its tool, its prompt and the facts it shows", () => {
  const ai = { ...PHOTO, origin: "AI_GENERATED" as const, generator: " ", prompt: "", claimIds: [] };
  expect(declarationProblems(ai)).toEqual(["Name the AI tool and model.", "Give the prompt.", "Choose the facts the picture shows."]);
  expect(declarationProblems({ ...ai, generator: "ChatGPT", prompt: "A vat", claimIds: ["c1"] })).toEqual([]);
});

test("a photograph needs a craft, a caption and a description, and sends no tool or prompt", () => {
  expect(declarationProblems({ ...PHOTO, craftSlug: "", caption: "  ", altText: "x" })).toEqual([
    "Choose the craft it shows.",
    "Write a caption.",
    "Describe the picture for readers who cannot see it."
  ]);
  expect(declarationBody(PHOTO)).toEqual({
    craftSlug: "Kutch-Ajrakh",
    stageId: null,
    claimIds: [],
    origin: "PHOTOGRAPH",
    generator: null,
    prompt: null,
    caption: "A printer lifts the block",
    altText: "Hands lifting a carved wooden block from red cloth",
    rightsConfirmed: true,
    termsVersion: IMAGE_TERMS_VERSION
  });
});

test("only PNG, JPEG or WebP pictures of 10 MB or less are sent", () => {
  const picture = (type: string, size: number) => ({ type, size }) as File;
  expect(fileProblem(picture("image/png", 2_000_000))).toBeNull();
  expect(fileProblem(picture("image/gif", 2_000))).toBe("Choose a PNG, JPEG or WebP picture.");
  expect(fileProblem(picture("image/jpeg", 11 * 1024 * 1024))).toBe("Choose a picture of 10 MB or less.");
});

test("a picture can be taken back only while it waits, because consent cannot be revoked", () => {
  expect(canWithdraw(VIEW)).toBe(true);
  expect(canWithdraw({ ...VIEW, status: "AWAITING_FILE" })).toBe(true);
  expect(canWithdraw({ ...VIEW, status: "APPROVED" })).toBe(false);
  expect(canWithdraw({ ...VIEW, status: "REJECTED" })).toBe(false);
});

test("the server's picture view parses, and an unknown status is refused", () => {
  expect(parseShape(imageContributionShape, VIEW)).toEqual(VIEW);
  expect(() => parseShape(imageContributionShape, { ...VIEW, status: "HIDDEN" })).toThrow();
});

test("the picture pages are guarded by the capabilities the API requires", () => {
  const gates = Object.fromEntries(ROUTE_GUARDS.map((guard) => [guard.path, guard.gate]));
  expect(gates["/contributions/pictures"]).toBe("require(PROPOSE_KNOWLEDGE)");
  expect(gates["/admin/pictures"]).toBe("require(REVIEW_CONTRIBUTIONS)");
});
