"use client";

import dynamic from "next/dynamic";
import { useMemo } from "react";

import type { CraftTab } from "@/lib/craftProfile";
import { shownStageNames } from "@/lib/processView";
import type { CraftProcess } from "@/lib/scienceContract";
import type { VoiceAvailability } from "@/lib/voiceContract";

const VoicePanel = dynamic(() => import("@/components/voice/VoicePanel").then((module) => module.VoicePanel), { ssr: false });

export type CraftVoiceProps = {
  open: boolean;
  onClose: () => void;
  craftSlug: string;
  availability: VoiceAvailability;
  process: CraftProcess | null;
  onTab: (tab: CraftTab) => void;
  onStage: (stageId: string) => void;
};

export function CraftVoice({ open, onClose, craftSlug, availability, process, onTab, onStage }: CraftVoiceProps) {
  const stages = useMemo(() => shownStageNames(process), [process]);
  const host = useMemo(() => ({ stages, showOnMap: () => onTab("region"), openStage: onStage }), [onStage, onTab, stages]);
  return <VoicePanel open={open} onClose={onClose} craftSlug={craftSlug} mode="HYBRID" availability={availability} host={host} />;
}
