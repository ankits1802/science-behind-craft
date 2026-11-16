"use client";

import Link from "next/link";
import { BookOpen, MessageCircleQuestion, Mic } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import type { CraftProfile } from "@/lib/types";

export function CraftHeader({ craft, onVoice }: { craft: CraftProfile["craft"]; onVoice?: () => void }) {
  const path = [craft.categoryName, craft.subCategoryName].filter(Boolean).join(" › ");
  return (
    <>
      <PageHeader
        title={craft.name}
        description={[craft.localName && craft.localName !== craft.name ? craft.localName : null, path].filter(Boolean).join(" · ") || undefined}
        icon={<BookOpen className="h-5 w-5" aria-hidden />}
        actions={
          <>
            {onVoice ? (
              <button type="button" className="field-button-secondary" onClick={onVoice} data-testid="voice-button">
                <Mic className="h-4 w-4" aria-hidden />
                Talk
              </button>
            ) : null}
            <Link href={`/ask?craft=${encodeURIComponent(craft.slug)}`} className="field-button">
              <MessageCircleQuestion className="h-4 w-4" aria-hidden />
              Ask about this craft
            </Link>
          </>
        }
      />
      <div className="mb-5 flex flex-wrap items-center gap-2 text-xs">
        {craft.giStatus === "GI" ? (
          <span className="rounded-full border border-evidence-300 bg-evidence-100 px-2.5 py-1 font-semibold text-evidence-800 dark:border-evidence-800 dark:bg-evidence-950 dark:text-evidence-200">
            GI registered
          </span>
        ) : null}
        {craft.stateOfPractice.map((state) => (
          <span key={state} className="rounded-full border border-line-200 bg-card px-2.5 py-1 font-medium text-ink-700">
            {state}
          </span>
        ))}
      </div>
    </>
  );
}
