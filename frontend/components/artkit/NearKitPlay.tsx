"use client";

import { nearBlock } from "@/components/answer/nearBlock";

import type { KitPlayProps } from "./KitPlay";

export const NearKitPlay = nearBlock<KitPlayProps>(() => import("@/components/artkit/KitPlay").then((loaded) => loaded.KitPlay), null);
