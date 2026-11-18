"use client";

import { CheckCircle2, Info, OctagonAlert, TriangleAlert, X, type LucideIcon } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

export type ToastTone = "info" | "success" | "warning" | "error";

export type ToastInput = {
  title: string;
  description?: string;
  tone?: ToastTone;
  duration?: number;
  id?: string;
};

export type ToastRecord = {
  id: string;
  title: string;
  description?: string;
  tone: ToastTone;
  duration: number;
};

type ToastContextValue = {
  toast: (input: ToastInput) => string;
  dismiss: (id: string) => void;
};

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

const MAX_VISIBLE = 3;

export const TOAST_DURATION: Record<ToastTone, number> = { info: 5000, success: 5000, warning: 8000, error: 0 };

const TONES: Record<ToastTone, { icon: LucideIcon; tile: string }> = {
  info: { icon: Info, tile: "bg-info-wash text-info" },
  success: { icon: CheckCircle2, tile: "bg-success-wash text-success" },
  warning: { icon: TriangleAlert, tile: "bg-warning-wash text-warning" },
  error: { icon: OctagonAlert, tile: "bg-error-wash text-error" }
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const counter = useRef(0);

  const dismiss = useCallback((id: string) => {
    setToasts((current) => current.filter((item) => item.id !== id));
  }, []);

  const toast = useCallback((input: ToastInput) => {
    counter.current += 1;
    const tone = input.tone ?? "info";
    const record: ToastRecord = {
      id: input.id ?? `toast-${counter.current}`,
      title: input.title,
      description: input.description,
      tone,
      duration: input.duration ?? TOAST_DURATION[tone]
    };
    setToasts((current) => [...current.filter((item) => item.id !== record.id), record].slice(-MAX_VISIBLE));
    return record.id;
  }, []);

  const value = useMemo(() => ({ toast, dismiss }), [toast, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed inset-x-4 z-toast flex flex-col items-center gap-2 sm:start-auto sm:end-4 sm:w-[min(24rem,calc(100vw-2rem))] sm:items-stretch"
        style={{ bottom: "calc(var(--bottom-nav-h, 0px) + 0.75rem)" }}
      >
        {toasts.map((item) => (
          <ToastCard key={item.id} toast={item} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside ToastProvider");
  return context;
}

export function ToastCard({ toast, onDismiss }: { toast: ToastRecord; onDismiss: (id: string) => void }) {
  const [paused, setPaused] = useState(false);
  const remaining = useRef(toast.duration);
  const startedAt = useRef(0);
  const dismiss = useCallback(() => onDismiss(toast.id), [onDismiss, toast.id]);

  useEffect(() => {
    if (paused || remaining.current <= 0) return;
    startedAt.current = Date.now();
    const timer = setTimeout(dismiss, remaining.current);
    return () => {
      clearTimeout(timer);
      remaining.current = Math.max(1, remaining.current - (Date.now() - startedAt.current));
    };
  }, [dismiss, paused]);

  const { icon: Icon, tile } = TONES[toast.tone];

  return (
    <div
      role={toast.tone === "error" ? "alert" : undefined}
      data-tone={toast.tone}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      className="kv-toast motion-enter pointer-events-auto"
    >
      <span aria-hidden className={`kv-toast-tile ${tile}`}>
        <Icon />
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-ui text-ui font-semibold text-ink-1">{toast.title}</p>
        {toast.description ? <p className="mt-0.5 font-ui text-ui font-normal text-ink-2">{toast.description}</p> : null}
      </div>
      <button type="button" onClick={dismiss} aria-label={`Dismiss: ${toast.title}`} className="kv-close -mt-2.5 -me-2">
        <X aria-hidden />
      </button>
    </div>
  );
}
