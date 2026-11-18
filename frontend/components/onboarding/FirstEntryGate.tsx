"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ArtisanProfileForm } from "@/components/onboarding/ArtisanProfileForm";
import { RecordingAgreement } from "@/components/onboarding/RecordingAgreement";
import { StudentProfileForm } from "@/components/onboarding/StudentProfileForm";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { fetchProfile, type ProfileView } from "@/lib/profileContract";
import { fetchPrivacyNotice } from "@/lib/signUp";
import type { User } from "@/lib/types";

async function acceptCurrentNotice(): Promise<void> {
  const notice = await fetchPrivacyNotice();
  await apiFetch<unknown>("/auth/consent", { method: "POST", body: JSON.stringify({ kind: "PRIVACY_NOTICE", noticeVersion: notice.version }) });
}

function Frame({ title, children, onSignOut }: { title: string; children: React.ReactNode; onSignOut: () => void }) {
  return (
    <main className="flex min-h-screen items-start justify-center bg-bg-0 px-4 py-10">
      <section className="panel grid w-full max-w-2xl gap-5 p-6" data-testid="first-entry">
        <h1 className="font-display text-xl font-bold text-ink-900">{title}</h1>
        {children}
        <ActionGroup>
          <Button type="button" variant="ghost" onClick={onSignOut}>
            Sign out
          </Button>
        </ActionGroup>
      </section>
    </main>
  );
}

export function FirstEntryGate({ user, onDone, onSignOut }: { user: User; onDone: () => void; onSignOut: () => void }) {
  const [profile, setProfile] = useState<ProfileView | null>(null);
  const [recording, setRecording] = useState<string | null>(null);

  useEffect(() => {
    fetchProfile().then(setProfile).catch(() => setProfile(null));
  }, []);

  if (recording) {
    return (
      <Frame title="Recording" onSignOut={onSignOut}>
        <RecordingAgreement language={recording} onDone={onDone} notNow={onDone} />
      </Frame>
    );
  }
  if (user.role === "ARTISAN") {
    return (
      <Frame title="Your craft" onSignOut={onSignOut}>
        <ArtisanProfileForm
          current={profile?.artisan ?? null}
          accountName={user.name}
          action="Continue"
          onSaved={(view) => setRecording(view.artisan?.spokenLanguage ?? "en")}
        />
      </Frame>
    );
  }
  return (
    <Frame title="Before you start" onSignOut={onSignOut}>
      <StudentProfileForm ageBand={profile?.student?.ageBand ?? null} gender={profile?.student?.gender ?? null} action="Continue" before={acceptCurrentNotice} onSaved={onDone} />
      <p className="text-sm text-ink-600">
        <Link href="/privacy" target="_blank" rel="noopener noreferrer" className="font-medium text-purple-700 underline underline-offset-2 dark:text-purple-300">
          Privacy notice
        </Link>
      </p>
    </Frame>
  );
}

export function GuardianHold({ onCheck, onSignOut }: { onCheck: () => void; onSignOut: () => void }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-bg-0 px-4">
      <section className="panel grid w-full max-w-md gap-4 p-6 text-center" data-testid="guardian-hold">
        <p className="text-sm text-ink-900">Your teacher needs to confirm that your parent or guardian agrees before you continue.</p>
        <ActionGroup>
          <Button type="button" onClick={onCheck}>
            Check again
          </Button>
          <Button type="button" variant="ghost" onClick={onSignOut}>
            Sign out
          </Button>
        </ActionGroup>
      </section>
    </main>
  );
}
