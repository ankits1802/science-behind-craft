"use client";

import type { ReactNode } from "react";

import { useAuth } from "@/components/AuthProvider";
import { BrandMark } from "@/components/BrandMark";
import { FirstPasswordGate } from "@/components/FirstPasswordGate";
import { FirstEntryGate, GuardianHold } from "@/components/onboarding/FirstEntryGate";
import { TwoStepVerificationCard } from "@/components/settings/TwoStepVerificationCard";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { mustChangePassword } from "@/lib/signIn";
import type { User } from "@/lib/types";

export function AccountGate({ user, children }: { user: User; children: ReactNode }) {
  const { retryMe, logout, markPasswordChanged } = useAuth();
  const signOut = () => {
    logout().catch(() => undefined);
  };
  if (mustChangePassword(user)) return <FirstPasswordLocked onDone={markPasswordChanged} onSignOut={signOut} />;
  if (user.twoFactorRequired && !user.twoFactorEnabled) return <TwoStepRequired onSignOut={signOut} />;
  if (user.profileRequired) return <FirstEntryGate user={user} onDone={retryMe} onSignOut={signOut} />;
  if (user.guardianConsentRequired) return <GuardianHold onCheck={retryMe} onSignOut={signOut} />;
  return <>{children}</>;
}

function FirstPasswordLocked({ onDone, onSignOut }: { onDone: () => void; onSignOut: () => void }) {
  return (
    <div className="grid min-h-screen place-items-center bg-ground px-4 py-12">
      <main id="main-content" tabIndex={-1} className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <BrandMark className="h-12 w-12 text-ink-1" />
          <h1 className="font-headline text-h2 text-ink-1">Set a new password</h1>
        </div>
        <section className="panel p-6">
          <FirstPasswordGate currentPassword="" onDone={onDone} onSignOut={onSignOut} />
        </section>
      </main>
    </div>
  );
}

function TwoStepRequired({ onSignOut }: { onSignOut: () => void }) {
  return (
    <div className="grid min-h-screen place-items-center bg-ground px-4 py-12">
      <main id="main-content" tabIndex={-1} className="w-full max-w-lg" data-testid="two-step-required">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <BrandMark className="h-12 w-12 text-ink-1" />
          <h1 className="font-headline text-h2 text-ink-1">Turn on two-step verification</h1>
          <p className="text-body-sm text-ink-3">Your role needs it.</p>
        </div>
        <TwoStepVerificationCard />
        <ActionGroup className="mt-6">
          <button type="button" className="field-button-secondary" onClick={onSignOut}>
            Sign out
          </button>
        </ActionGroup>
      </main>
    </div>
  );
}
