"use client";

import { useState } from "react";
import { Presentation } from "lucide-react";

import { deleteConfirm, useConfirm } from "@/components/dialogs/ConfirmDialog";
import { failureMessage, useRemote } from "@/components/hooks/useRemote";
import { LessonList } from "@/components/learn/LessonList";
import { PageHeader } from "@/components/PageHeader";
import { LoadingPanel, RetryPanel } from "@/components/RemotePanels";
import { apiErrorMessage } from "@/lib/api";
import { deleteLesson, fetchLessons } from "@/lib/lessonApi";
import type { LessonSummary } from "@/lib/lessonContract";

const DELETE_FAILED = "Couldn't delete the lesson. Try again.";

export default function LessonsPage() {
  const lessons = useRemote(fetchLessons);
  const confirm = useConfirm();
  const [gone, setGone] = useState<ReadonlySet<string>>(() => new Set());
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function remove(lesson: LessonSummary) {
    if (!(await confirm(deleteConfirm(`Delete “${lesson.title}”?`, "Its slides and files go with it.")))) return;
    setBusy(lesson.id);
    setError(null);
    try {
      await deleteLesson(lesson.id);
      setGone((current) => new Set([...current, lesson.id]));
    } catch (cause) {
      setError(apiErrorMessage(cause, DELETE_FAILED));
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader title="Lessons" icon={<Presentation className="h-5 w-5" aria-hidden />} back={false} />
      {error ? (
        <p role="alert" className="mb-4 rounded-md border border-red-200 bg-error-100 px-3 py-2 text-sm text-error-600">
          {error}
        </p>
      ) : null}
      {lessons.failure ? (
        <RetryPanel message={failureMessage(lessons.failure, "Couldn't load your lessons.")} onRetry={lessons.retry} />
      ) : lessons.data ? (
        <LessonList lessons={lessons.data.items.filter((lesson) => !gone.has(lesson.id))} busy={busy} onDelete={(lesson) => void remove(lesson)} />
      ) : (
        <LoadingPanel />
      )}
    </>
  );
}
