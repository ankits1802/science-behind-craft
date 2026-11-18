"use client";

import { useEffect, useState } from "react";
import { Mic, UserRound } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { ArtisanProfileForm } from "@/components/onboarding/ArtisanProfileForm";
import { RecordingAgreement } from "@/components/onboarding/RecordingAgreement";
import { StudentProfileForm } from "@/components/onboarding/StudentProfileForm";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { apiErrorMessage } from "@/lib/api";
import { fetchProfile, withdrawRecording, type ProfileView } from "@/lib/profileContract";

function CardTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="grid h-8 w-8 place-items-center rounded-md bg-purple-950 text-purple-100">{icon}</span>
      <h2 className="font-display font-bold text-ink-900">{title}</h2>
    </div>
  );
}

function RecordingStatus({ profile, onChanged }: { profile: ProfileView; onChanged: () => void }) {
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const artisan = profile.artisan;
  if (!artisan) return null;
  if (!artisan.recordingConsent) {
    return <RecordingAgreement language={artisan.spokenLanguage ?? "en"} onDone={onChanged} />;
  }

  async function withdraw() {
    try {
      const done = await withdrawRecording();
      setMessage(`Taken back: ${done.withdrawnContributions} facts, ${done.deletedConversations} conversations.`);
      onChanged();
    } catch (cause) {
      setMessage(apiErrorMessage(cause, "Couldn't withdraw. Try again."));
    } finally {
      setConfirming(false);
    }
  }

  return (
    <div className="grid gap-2">
      <p className="text-sm text-ink-700">You agreed to be recorded.</p>
      {confirming ? <p className="text-sm text-ink-900">This deletes every recording and takes back every fact you shared.</p> : null}
      {message ? <p role="status" className="text-sm text-ink-700">{message}</p> : null}
      <ActionGroup>
        {confirming ? (
          <>
            <Button type="button" variant="destructive" onClick={() => void withdraw()}>
              Withdraw
            </Button>
            <Button type="button" variant="outline" onClick={() => setConfirming(false)}>
              Keep
            </Button>
          </>
        ) : (
          <Button type="button" variant="outline" onClick={() => setConfirming(true)}>
            Withdraw agreement
          </Button>
        )}
      </ActionGroup>
    </div>
  );
}

export function ProfileCards() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<ProfileView | null>(null);
  const [saved, setSaved] = useState(false);

  function load() {
    fetchProfile().then(setProfile).catch(() => setProfile(null));
  }

  useEffect(load, []);

  function stored(view: ProfileView) {
    setProfile(view);
    setSaved(true);
  }

  if (!user || !profile) return null;
  if (profile.student) {
    return (
      <section className="panel flex h-full flex-col gap-3 p-5" data-testid="student-profile-card">
        <CardTitle icon={<UserRound className="h-4 w-4" aria-hidden />} title="Your profile" />
        <StudentProfileForm ageBand={profile.student.ageBand} gender={profile.student.gender} action="Save" onSaved={stored} />
        {saved ? <p role="status" className="text-sm text-ink-700">Saved.</p> : null}
      </section>
    );
  }
  if (!profile.artisan) return null;
  return (
    <section className="panel flex h-full flex-col gap-3 p-5 lg:col-span-2" data-testid="artisan-profile-card">
      <CardTitle icon={<Mic className="h-4 w-4" aria-hidden />} title="Your craft profile" />
      <ArtisanProfileForm current={profile.artisan} accountName={user.name} action="Save" onSaved={stored} />
      {saved ? <p role="status" className="text-sm text-ink-700">Saved.</p> : null}
      <RecordingStatus profile={profile} onChanged={load} />
    </section>
  );
}
