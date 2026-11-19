import type { ReactNode } from "react";
import { CircleAlert, Clock, Info, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export type FormAlertTone = "error" | "warning" | "info";

const TONE: Record<FormAlertTone, { box: string; icon: string; Icon: LucideIcon }> = {
  error: { box: "border-error bg-error-wash", icon: "text-error", Icon: CircleAlert },
  warning: { box: "border-warning bg-warning-wash", icon: "text-warning", Icon: Clock },
  info: { box: "border-info bg-info-wash", icon: "text-info", Icon: Info }
};

export function FormAlert({ tone = "error", title, children, className, testId }: { tone?: FormAlertTone; title?: ReactNode; children: ReactNode; className?: string; testId?: string }) {
  const look = TONE[tone];
  const Icon = look.Icon;
  return (
    <div role="alert" data-testid={testId} className={cn("flex items-start gap-2.5 rounded-control border px-3 py-2.5 font-ui text-ui text-ink-1", look.box, className)}>
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", look.icon)} aria-hidden />
      <div className="grid min-w-0 gap-1">
        {title ? <p className="m-0 font-semibold">{title}</p> : null}
        <div className="leading-normal">{children}</div>
      </div>
    </div>
  );
}

export function LiveAlert({ message, className }: { message: string | null; className?: string }) {
  if (!message) return <div role="alert" className="sr-only" />;
  return <FormAlert className={className}>{message}</FormAlert>;
}
