"use client";

import { usePathname } from "next/navigation";
import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { UserRound } from "lucide-react";

import { ControlCount } from "@/components/nav/navBadges";
import { AnchoredPopover } from "@/components/ui/AnchoredPopover";
import { Button } from "@/components/ui/button";
import { ToggleSwitch } from "@/components/ui/Toggle";
import { focusableIn } from "@/lib/focusable";

export const ACCOUNT_LABEL = "Account";

export type AccountView = {
  name: string;
  role: string;
  adminToggle: { checked: boolean; onChange: () => void } | null;
  onSignOut: () => void;
};

export function AccountPanel({ account, children }: { account: AccountView; children?: ReactNode }) {
  return (
    <div className="grid" data-testid="account-panel">
      <div className="px-3 pb-1 pt-1.5">
        <p className="m-0 truncate font-ui text-ui font-semibold text-ink-1">{account.name}</p>
        <p className="m-0 font-ui text-label text-ink-3">{account.role}</p>
      </div>
      {children}
      <div className="kv-menu-account">
        {account.adminToggle ? (
          <div className="px-3">
            <ToggleSwitch label="Admin view" showLabel checked={account.adminToggle.checked} onChange={account.adminToggle.onChange} />
          </div>
        ) : null}
        <div className="px-3 pb-1">
          <Button variant="quiet" size="sm" onClick={account.onSignOut} className="w-full">
            Sign out
          </Button>
        </div>
      </div>
    </div>
  );
}

export function AccountMenu({ count = 0, children }: { count?: number; children: (close: () => void) => ReactNode }) {
  const [open, setOpen] = useState(false);
  const anchorRef = useRef<HTMLButtonElement | null>(null);
  const panelId = useId();
  const pathname = usePathname();
  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    const frame = requestAnimationFrame(() => {
      const [first] = focusableIn(document.getElementById(panelId));
      first?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [open, panelId]);

  return (
    <>
      <button
        ref={anchorRef}
        type="button"
        className="kv-bar-acct"
        aria-label={ACCOUNT_LABEL}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((value) => !value)}
        data-testid="account-button"
      >
        <UserRound aria-hidden />
        <ControlCount count={count} />
      </button>
      <AnchoredPopover open={open} onClose={close} anchorRef={anchorRef} label={ACCOUNT_LABEL} panelId={panelId} maxWidth={320} className="w-80 p-2">
        {children(close)}
      </AnchoredPopover>
    </>
  );
}
