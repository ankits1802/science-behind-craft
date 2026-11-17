"use client";

import Link from "next/link";
import { Presentation } from "lucide-react";

import { ActionGroup } from "@/components/ui/ActionGroup";
import { formatDate } from "@/lib/format";
import type { LessonSummary } from "@/lib/lessonContract";
import { lessonHref, slideCountText } from "@/lib/lessonView";
import { SAVED_PATH } from "@/lib/savedView";

function LessonRow({ lesson, busy, onDelete }: { lesson: LessonSummary; busy: boolean; onDelete: (lesson: LessonSummary) => void }) {
  return (
    <li className="panel grid min-w-0 gap-2 p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-center md:gap-4 md:p-5" data-testid="lesson-row">
      <div className="grid min-w-0 gap-1">
        <Link href={lessonHref(lesson.id)} className="min-w-0 break-words font-display text-base font-bold text-ink-900 underline-offset-2 hover:text-purple-700 hover:underline">
          {lesson.title}
        </Link>
        <p className="flex flex-wrap gap-x-2 gap-y-1 text-xs text-ink-500">
          {lesson.craft ? <span className="font-medium text-ink-700">{lesson.craft.name}</span> : null}
          <span>{slideCountText(lesson.slideCount)}</span>
          <span>Version {lesson.version}</span>
          <span>{formatDate(lesson.createdAt)}</span>
        </p>
      </div>
      <ActionGroup inline align="end">
        <button type="button" data-danger className="field-danger" disabled={busy} onClick={() => onDelete(lesson)} data-testid="lesson-delete">
          Delete
        </button>
      </ActionGroup>
    </li>
  );
}

export function LessonList({ lessons, busy, onDelete }: { lessons: readonly LessonSummary[]; busy: string | null; onDelete: (lesson: LessonSummary) => void }) {
  if (lessons.length === 0) {
    return (
      <div className="panel grid justify-items-center gap-3 p-6 text-center" data-testid="lessons-empty">
        <Presentation className="h-5 w-5 text-purple-700 dark:text-purple-300" aria-hidden />
        <p className="text-sm text-ink-700">No lessons yet.</p>
        <Link href={SAVED_PATH} className="field-button">
          Open saved answers
        </Link>
      </div>
    );
  }
  return (
    <ul className="grid min-w-0 gap-3" data-testid="lesson-list">
      {lessons.map((lesson) => (
        <LessonRow key={lesson.id} lesson={lesson} busy={busy === lesson.id} onDelete={onDelete} />
      ))}
    </ul>
  );
}
