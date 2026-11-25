"use client";

import { nearBlock } from "@/components/answer/nearBlock";

import type { CodedFrameProps } from "./CodedFrame";

export const NearCodedFrame = nearBlock<CodedFrameProps>(() => import("@/components/monograph/kinds/science/CodedFrame").then((loaded) => loaded.CodedFrame), null);
