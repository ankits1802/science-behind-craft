"use client";

import { Suspense, useMemo } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Presentation } from "lucide-react";

import { failureMessage, useRemote } from "@/components/hooks/useRemote";
import { LessonBuilder } from "@/components/learn/LessonBuilder";
import { PageHeader } from "@/components/PageHeader";
import { LoadingPanel, RetryPanel } from "@/components/RemotePanels";
import { fetchExplainerDocument } from "@/lib/learningApi";
import { lessonHref } from "@/lib/lessonView";
import { EXPLAINER_PARAM, SAVED_PATH, VERSION_PARAM } from "@/lib/savedView";
import { positiveParam } from "@/lib/searchParams";

export default function NewLessonPage() {
  return (
    <Suspense fallback={null}>
      <NewLesson />
    </Suspense>
  );
}

function NewLesson() {
  const params = useSearchParams();
  const router = useRouter();
  const explainerId = params.get(EXPLAINER_PARAM);
  const version = positiveParam(params.get(VERSION_PARAM));
  const load = useMemo(() => (explainerId ? () => fetchExplainerDocument(explainerId, version) : null), [explainerId, version]);
  const document = useRemote(load);
  const header = <PageHeader title="Make a lesson" description={document.data?.explainer.question} icon={<Presentation className="h-5 w-5" aria-hidden />} />;

  if (!explainerId) {
    return (
      <>
        {header}
        <div className="panel grid justify-items-center gap-3 p-6 text-center">
          <p className="text-sm text-ink-700">Choose an explainer first.</p>
          <Link href={SAVED_PATH} className="field-button">
            Open saved answers
          </Link>
        </div>
      </>
    );
  }
  return (
    <>
      {header}
      {document.failure ? (
        <RetryPanel message={failureMessage(document.failure, "Couldn't open that explainer.")} onRetry={document.retry} />
      ) : document.data ? (
        <LessonBuilder document={document.data} onBuilt={(pack) => router.replace(lessonHref(pack.id))} />
      ) : (
        <LoadingPanel />
      )}
    </>
  );
}
