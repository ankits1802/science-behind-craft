"use client";

import { Pause, Play } from "lucide-react";

import { Button } from "@/components/ui/button";

export type PlayPauseProps = { playing: boolean; motion: boolean; onToggle: () => void; testId: string };

export function PlayPauseButton({ playing, motion, onToggle, testId }: PlayPauseProps) {
  return (
    <Button variant="quiet" size="sm" aria-pressed={motion ? playing : undefined} onClick={onToggle} data-testid={testId}>
      {playing ? <Pause className="size-3.5" aria-hidden /> : <Play className="size-3.5" aria-hidden />}
      <span>{playing ? "Pause" : "Play"}</span>
    </Button>
  );
}
