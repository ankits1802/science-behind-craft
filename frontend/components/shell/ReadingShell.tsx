"use client";

import type { ReactNode } from "react";

import { useAuth } from "@/components/AuthProvider";
import { DynamicIslandNav } from "@/components/DynamicIslandNav";
import { ReadingBar } from "@/components/nav/ReadingBar";
import { AccountGate } from "@/components/shell/AccountGate";
import { ShellFrame } from "@/components/shell/ShellFrame";

export function ReadingShell({ children }: { children: ReactNode }) {
  const { user, loading, reach, retryMe } = useAuth();
  const onRetry = reach === "retrying" ? retryMe : null;
  if (!user) {
    return (
      <ShellFrame nav={<ReadingBar signIn={!loading} />} onRetry={onRetry}>
        {children}
      </ShellFrame>
    );
  }
  return (
    <AccountGate user={user}>
      <ShellFrame nav={<DynamicIslandNav />} onRetry={onRetry}>
        {children}
      </ShellFrame>
    </AccountGate>
  );
}
