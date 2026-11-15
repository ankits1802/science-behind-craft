"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { BrandMark } from "@/components/BrandMark";
import { Markdown } from "@/components/Markdown";
import { formatDate } from "@/lib/format";
import { fetchPrivacyNotice, type PrivacyNotice } from "@/lib/signUp";

export default function PrivacyPage() {
  const [notice, setNotice] = useState<PrivacyNotice | null>(null);
  const [failed, setFailed] = useState(false);
  const [round, setRound] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    fetchPrivacyNotice()
      .then((next) => {
        if (!cancelled) setNotice(next);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [round]);

  return (
    <div className="min-h-dvh bg-bg-0 px-4 py-10">
      <main id="main-content" className="mx-auto max-w-3xl">
        <Link href="/" className="mb-8 inline-flex items-center gap-2 text-ink-900">
          <BrandMark className="h-9 w-9 rounded-lg" />
          <span className="font-display text-lg font-bold tracking-tight">KalaVigyan</span>
        </Link>
        <article className="panel p-6 md:p-8">
          {notice ? (
            <>
              <h1 className="display-title text-3xl">{notice.title}</h1>
              <p className="mt-2 text-xs text-ink-500">
                Version {notice.version}
                {notice.publishedAt ? ` · ${formatDate(notice.publishedAt)}` : ""}
              </p>
              <div className="mt-6 text-sm text-ink-700">
                <Markdown text={notice.body} />
              </div>
            </>
          ) : failed ? (
            <div role="alert" className="grid justify-items-center gap-3 py-6 text-center">
              <p className="text-sm text-ink-700">Couldn&apos;t load the privacy notice.</p>
              <button type="button" className="field-button" onClick={() => setRound((value) => value + 1)}>
                Try again
              </button>
            </div>
          ) : (
            <p className="text-sm text-ink-500">Loading…</p>
          )}
        </article>
      </main>
    </div>
  );
}
