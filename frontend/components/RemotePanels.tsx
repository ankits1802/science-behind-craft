"use client";

import type { ReactNode } from "react";
import { RotateCw } from "lucide-react";

import type { Remote, RemoteFailure } from "@/components/hooks/useRemote";
import { cn } from "@/lib/utils";

export function LoadingPanel({ className }: { className?: string }) {
  return (
    <section role="status" className={cn("panel p-6 text-sm text-ink-500", className)}>
      Loading…
    </section>
  );
}

export function RetryPanel({ message, onRetry, className }: { message: string; onRetry: () => void; className?: string }) {
  return (
    <section role="alert" className={cn("panel grid justify-items-center gap-3 p-6 text-center", className)}>
      <p className="text-sm text-ink-700">{message}</p>
      <button type="button" className="field-button" onClick={onRetry}>
        <RotateCw className="h-4 w-4" aria-hidden />
        Try again
      </button>
    </section>
  );
}

export function RemoteView<T>({
  remote,
  failed,
  children
}: {
  remote: Remote<T>;
  failed: (failure: RemoteFailure) => string;
  children: (data: T) => ReactNode;
}) {
  if (remote.failure) return <RetryPanel message={failed(remote.failure)} onRetry={remote.retry} />;
  if (remote.data === null) return <LoadingPanel />;
  return <>{children(remote.data)}</>;
}
