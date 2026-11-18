"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { EyeOff, Lock } from "lucide-react";

import {
  adminChromeRouteFor,
  adminChromeVisible,
  useAdminView,
  type AdminChromeRoute
} from "@/components/AdminViewProvider";
import { useAuth } from "@/components/AuthProvider";
import { DeadEndFrame, ErrorState } from "@/components/DeadEnd";
import { DynamicIslandNav } from "@/components/DynamicIslandNav";
import { ErrorPanel } from "@/components/ErrorPanel";
import { AccountGate } from "@/components/shell/AccountGate";
import { ShellFrame } from "@/components/shell/ShellFrame";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { browserOffline } from "@/lib/errorKind";
import { hasAdminView, routeGuardFor } from "@/lib/permissions";
import { signInHref } from "@/lib/sessionReturn";
import type { User } from "@/lib/types";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, reach, retryMe } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user && reach === "ok") router.replace(signInHref(`${window.location.pathname}${window.location.search}`));
  }, [loading, reach, router, user]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-bg-0 text-sm text-ink-500">
        Loading…
      </main>
    );
  }

  if (!user && reach === "retrying") return <Unreachable onRetry={retryMe} />;

  if (!user) return null;

  return (
    <AccountGate user={user}>
      <ShellFrame nav={<DynamicIslandNav />} onRetry={reach === "retrying" ? retryMe : null}>
        <GuardedRoute user={user}>{children}</GuardedRoute>
      </ShellFrame>
    </AccountGate>
  );
}

function GuardedRoute({ user, children }: { user: User; children: React.ReactNode }) {
  const { adminMode, adminViewResolved, setAdminView } = useAdminView();
  const pathname = usePathname();
  const guard = routeGuardFor(pathname);
  if (guard && !guard.can(user)) return <RouteLocked title={guard.title} message={guard.message} />;
  const chrome = adminChromeRouteFor(pathname);
  if (chrome && hasAdminView(user) && !adminViewResolved) {
    return <section className="panel p-6 text-sm text-ink-500">Checking your admin view…</section>;
  }
  if (chrome && !adminChromeVisible(user, adminMode)) return <AdminViewHidden route={chrome} onEnable={() => setAdminView(true)} />;
  return <>{children}</>;
}

function Unreachable({ onRetry }: { onRetry: () => void }) {
  return (
    <div role="alert" data-testid="unreachable">
      <DeadEndFrame nav={false}>
        <ErrorState kind={browserOffline() ? "offline" : "unavailable"} onRetry={onRetry} />
      </DeadEndFrame>
    </div>
  );
}

function RouteLocked({ title, message }: { title: string; message: string }) {
  return (
    <ErrorPanel screen="forbidden" tone="notice" icon={<Lock className="h-5 w-5" aria-hidden />} title={title} line={message}>
      <Link href="/ask" className="field-button">
        Home
      </Link>
    </ErrorPanel>
  );
}

function AdminViewHidden({ route, onEnable }: { route: AdminChromeRoute; onEnable: () => void }) {
  return (
    <section className="panel px-6 py-14 text-center" aria-live="polite">
      <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full bg-surface-50 text-ink-500">
        <EyeOff className="h-5 w-5" aria-hidden />
      </div>
      <h1 className="font-display text-xl font-bold tracking-tight text-ink-900">
        {route.label} is hidden while admin view is off
      </h1>
      <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-ink-500">
        {route.blurb} Turn admin view on to open it.
      </p>
      <ActionGroup className="mt-7">
        <button type="button" onClick={onEnable} className="field-button">
          Turn admin view back on
        </button>
        {route.alternative ? (
          <Link href={route.alternative.href} className="field-button-secondary">
            {route.alternative.label}
          </Link>
        ) : null}
        <Link href="/ask" className="field-button-secondary">
          Home
        </Link>
      </ActionGroup>
    </section>
  );
}
