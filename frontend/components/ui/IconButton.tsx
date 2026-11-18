import * as React from "react";

import { cn } from "@/lib/utils";

export type IconButtonProps = Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "aria-label" | "children"> & {
  label: string;
  icon: React.ReactNode;
  edge?: boolean;
  onPhoto?: boolean;
};

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(({ label, icon, edge = false, onPhoto = false, className, type = "button", ...props }, ref) => (
  <button
    ref={ref}
    type={type}
    aria-label={label}
    title={label}
    className={cn("kv-btn", className)}
    data-shape="icon"
    data-variant={edge ? "quiet" : "plain"}
    data-on-photo={onPhoto ? "" : undefined}
    {...props}
  >
    <span aria-hidden className="contents">
      {icon}
    </span>
  </button>
));
IconButton.displayName = "IconButton";
