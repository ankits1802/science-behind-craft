import { Loader2 } from "lucide-react";

import type { AnswerStatus } from "@/lib/types";

export function AnswerProgress({ status, writing }: { status: AnswerStatus | null; writing: boolean }) {
  const message = status?.message ?? (writing ? "Writing" : "Starting");
  return (
    <p className="flex items-center gap-2 text-sm text-ink-500" role="status" aria-live="polite" data-testid="answer-progress" data-step={status?.step}>
      <Loader2 className="h-4 w-4 shrink-0 animate-spin motion-reduce:animate-none" aria-hidden />
      <span>{message}…</span>
    </p>
  );
}
