"use client";

import Link from "next/link";
import { BookMarked, ListOrdered, MapPinned } from "lucide-react";

import { ActionGroup } from "@/components/ui/ActionGroup";
import type { ClientToolCall, VoiceTurn } from "@/lib/voiceContract";
import { toolCallSignature } from "@/lib/voiceRules";

export type TurnActionContext = {
  craftSlug: string | null;
  stages: ReadonlyMap<string, string>;
  showOnMap?: () => void;
  openStage?: (stageId: string) => void;
  showSources: (answerId: string) => void;
};

const CHIP = "field-button-secondary min-h-9 px-3 py-1.5 text-xs";

function chipFor(call: ClientToolCall, turn: VoiceTurn, context: TurnActionContext) {
  const key = toolCallSignature(call);
  switch (call.name) {
    case "show_sources":
      if (call.parameters.answerId !== turn.answerId) return null;
      return (
        <button key={key} type="button" className={CHIP} onClick={() => context.showSources(call.parameters.answerId)}>
          <BookMarked className="h-3.5 w-3.5" aria-hidden />
          Sources
        </button>
      );
    case "show_on_map":
      if (call.parameters.craftSlug !== context.craftSlug) return null;
      if (context.showOnMap) {
        return (
          <button key={key} type="button" className={CHIP} onClick={context.showOnMap}>
            <MapPinned className="h-3.5 w-3.5" aria-hidden />
            Map
          </button>
        );
      }
      return (
        <Link key={key} href={`/crafts/${encodeURIComponent(call.parameters.craftSlug)}?tab=region`} className={CHIP}>
          <MapPinned className="h-3.5 w-3.5" aria-hidden />
          Map
        </Link>
      );
    case "open_stage": {
      const name = context.stages.get(call.parameters.stageId);
      const open = context.openStage;
      if (!name || !open) return null;
      return (
        <button key={key} type="button" className={CHIP} onClick={() => open(call.parameters.stageId)}>
          <ListOrdered className="h-3.5 w-3.5" aria-hidden />
          {name}
        </button>
      );
    }
    case "offer_image":
      return null;
  }
}

export function VoiceTurnActions({ turn, context }: { turn: VoiceTurn; context: TurnActionContext }) {
  const seen = new Set<string>();
  const unique = turn.actions.filter((call) => {
    const signature = toolCallSignature(call);
    if (seen.has(signature)) return false;
    seen.add(signature);
    return true;
  });
  return (
    <ActionGroup align="start" inline>
      {unique.map((call) => chipFor(call, turn, context))}
    </ActionGroup>
  );
}
