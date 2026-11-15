"use client";

import { Settings as SettingsIcon } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { PageHeader } from "@/components/PageHeader";
import { ChangePasswordCard } from "@/components/settings/ChangePasswordCard";
import { AccessibilityCard, AppearanceCard } from "@/components/settings/PersonalSettingsCards";
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
        <AppearanceCard />
        <AccessibilityCard />
        <TwoStepVerificationCard />
        <ChangePasswordCard />
      </div>
    </>
  );
}
