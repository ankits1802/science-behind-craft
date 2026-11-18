"use client";

import { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Presentation } from "lucide-react";

import { CitedReading } from "@/components/answer/CitedReading";
import { useAskConfig } from "@/components/ask/useAskConfig";
import { deleteConfirm, useConfirm } from "@/components/dialogs/ConfirmDialog";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { failureMessage, useRemote } from "@/components/hooks/useRemote";
import { LessonPackView } from "@/components/learn/LessonPackView";
import { ShareControl } from "@/components/learn/ShareControl";
import { PageHeader } from "@/components/PageHeader";
import { LoadingPanel, RetryPanel } from "@/components/RemotePanels";
import { apiErrorMessage } from "@/lib/api";
import { languageFor } from "@/lib/answerLanguages";
import { listedSourceNumbers } from "@/lib/citations";
import { deleteLesson, fetchLesson } from "@/lib/lessonApi";
import { LESSONS_HOME } from "@/lib/lessonView";
import { LESSON_SHARE_PATH } from "@/lib/shareContract";

export default function LessonPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const reduce = useAppReducedMotion();
  const confirm = useConfirm();
  const { config } = useAskConfig();
  const load = useMemo(() => () => fetchLesson(id), [id]);
  const lesson = useRemote(load);
  const pack = lesson.data;
  const numbers = useMemo(() => listedSourceNumbers(pack?.sources ?? []), [pack]);
  const [error, setError] = useState<string | null>(null);

  async function remove() {
    if (!pack || !(await confirm(deleteConfirm(`Delete “${pack.title}”?`, "Its slides and files go with it.")))) return;
    try {
      await deleteLesson(pack.id);
      router.replace(LESSONS_HOME);
    } catch (cause) {
      setError(apiErrorMessage(cause, "Couldn't delete the lesson. Try again."));
    }
  }

  const actions = pack ? (
    <>
      <ShareControl sharePath={LESSON_SHARE_PATH(pack.id)} kind="lesson" />
      <button type="button" data-danger className="field-danger" onClick={() => void remove()}>
        Delete
      </button>
    </>
  ) : null;

  return (
    <>
      <PageHeader title={pack?.title ?? "Lesson"} icon={<Presentation className="h-5 w-5" aria-hidden />} actions={actions} />
      {error ? (
        <p role="alert" className="mb-4 rounded-md border border-red-200 bg-error-100 px-3 py-2 text-sm text-error-600">
          {error}
        </p>
      ) : null}
      {lesson.failure ? (
        <RetryPanel message={failureMessage(lesson.failure, "Couldn't open that lesson.")} onRetry={lesson.retry} />
      ) : pack ? (
        <CitedReading sources={pack.sources} numbers={numbers} language={languageFor(pack.language, config.languages)}>
          <LessonPackView pack={pack} reduce={reduce} />
        </CitedReading>
      ) : (
        <LoadingPanel />
      )}
    </>
  );
}
