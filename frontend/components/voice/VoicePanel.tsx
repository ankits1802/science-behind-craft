"use client";

import { Mic } from "lucide-react";

import { FieldDialog } from "@/components/dialogs/FieldDialog";
import { ActionGroup } from "@/components/ui/ActionGroup";
import type { AnswerMode } from "@/lib/types";

export type VoicePanelProps = {
  open: boolean;
  onClose: () => void;
  craftSlug: string | null;
  mode: AnswerMode;
  language: string;
  onTranscript?: (text: string) => void;
};

export function VoicePanel({ open, onClose }: VoicePanelProps) {
  return (
    <FieldDialog
      open={open}
      onClose={onClose}
      title="Voice"
      className="max-w-sm"
      footer={
        <ActionGroup>
          <button type="button" className="field-button" onClick={onClose}>
            End
          </button>
        </ActionGroup>
      }
    >
      <div className="grid place-items-center py-6" data-testid="voice-panel">
        <span className="relative grid h-28 w-28 place-items-center rounded-full bg-purple-950 text-purple-100 ring-8 ring-purple-100 dark:ring-purple-900">
          <span aria-hidden className="absolute inset-0 rounded-full motion-safe:animate-ping bg-purple-700/20" />
          <Mic className="relative h-8 w-8" aria-hidden />
        </span>
      </div>
    </FieldDialog>
  );
}
