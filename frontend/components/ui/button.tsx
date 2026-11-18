import * as React from "react";

import { cn } from "@/lib/utils";

export type ButtonLook = "primary" | "quiet" | "danger" | "destroy" | "text";

export type ButtonVariant = ButtonLook | "default" | "destructive" | "outline" | "secondary" | "ghost" | "link" | "provider";

export type ButtonSize = "md" | "sm" | "default" | "lg" | "icon" | "auth";

const LOOK: Record<ButtonVariant, ButtonLook> = {
  primary: "primary",
  quiet: "quiet",
  danger: "danger",
  destroy: "destroy",
  text: "text",
  default: "primary",
  destructive: "destroy",
  outline: "quiet",
  secondary: "quiet",
  ghost: "quiet",
  link: "text",
  provider: "quiet"
};

export type ButtonLookProps = {
  className: string;
  "data-variant": ButtonLook;
  "data-size"?: "sm";
  "data-shape"?: "icon";
  "data-on-photo"?: "";
};

export function buttonLook({ variant = "quiet", size = "md", onPhoto = false, className }: { variant?: ButtonVariant; size?: ButtonSize; onPhoto?: boolean; className?: string } = {}): ButtonLookProps {
  return {
    className: cn("kv-btn", className),
    "data-variant": LOOK[variant],
    ...(size === "sm" ? { "data-size": "sm" as const } : {}),
    ...(size === "icon" ? { "data-shape": "icon" as const } : {}),
    ...(onPhoto ? { "data-on-photo": "" as const } : {})
  };
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  busy?: boolean;
  busyLabel?: React.ReactNode;
  onPhoto?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant = "default", size = "md", busy = false, busyLabel, onPhoto = false, type = "button", onClick, children, ...props }, ref) => (
  <button
    ref={ref}
    type={type}
    aria-busy={busy || undefined}
    onClick={(event) => {
      if (busy) {
        event.preventDefault();
        return;
      }
      onClick?.(event);
    }}
    {...buttonLook({ variant, size, onPhoto, className })}
    {...props}
  >
    {busy || busyLabel ? (
      <span className="kv-btn-label">
        <span data-rest="">{children}</span>
        <span data-busy="" aria-hidden={!busy}>
          <span className="kv-spin" aria-hidden />
          {busyLabel ?? children}
        </span>
      </span>
    ) : (
      children
    )}
  </button>
));
Button.displayName = "Button";

export { Button };
