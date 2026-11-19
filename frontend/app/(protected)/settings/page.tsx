"use client";

import { Settings as SettingsIcon } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { PageHeader } from "@/components/PageHeader";
import { AlertDigestCard } from "@/components/settings/AlertDigestCard";
import { ChangePasswordCard } from "@/components/settings/ChangePasswordCard";
import { ConnectedClientsCard } from "@/components/settings/ConnectedClientsCard";
import { AccessibilityCard, AppearanceCard } from "@/components/settings/PersonalSettingsCards";
import { ProfileCards } from "@/components/settings/ProfileCards";
import { TwoStepVerificationCard } from "@/components/settings/TwoStepVerificationCard";
import { roleLabel } from "@/lib/permissions";

export default function SettingsPage() {
  const { user } = useAuth();
  return (
    <>
      <PageHeader
        title="Settings"
        description={user ? `${user.name || user.email} · ${roleLabel(user.role)}` : undefined}
        icon={<SettingsIcon className="h-5 w-5" aria-hidden />}
        back={false}
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <ProfileCards />
        <AppearanceCard />
        <AccessibilityCard />
        <TwoStepVerificationCard />
        <ChangePasswordCard />
        <AlertDigestCard />
        <ConnectedClientsCard />
      </div>
    </>
  );
}
