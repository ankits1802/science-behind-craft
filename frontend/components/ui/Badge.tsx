import type { ReactNode } from "react";

export type BadgeTone = "note" | "attention";

const TONE_CLASS: Record<BadgeTone, string> = {
  note: "border-rule-strong text-ink-2",
  attention: "border-warning bg-warning-wash text-warning"
};

export function Badge({
  tone = "note",
  as: Tag = "span",
  className,
  children
}: {
  tone?: BadgeTone;
  as?: "span" | "dd";
  className?: string;
  children: ReactNode;
}) {
  return (
    <Tag
      className={`w-fit rounded-plate border px-1.5 py-px font-ui text-caption font-semibold tracking-[0.04em] ${TONE_CLASS[tone]}${className ? ` ${className}` : ""}`}
    >
      {children}
    </Tag>
  );
}
