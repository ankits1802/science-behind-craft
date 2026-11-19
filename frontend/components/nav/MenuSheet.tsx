"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useId, useState, type ReactNode } from "react";
import { Menu, X } from "lucide-react";

import { ControlCount } from "@/components/nav/navBadges";
import { Sheet } from "@/components/ui/Sheet";

export const MENU_LABEL = "Menu";

export type MenuEntry = { href: string; label: string; current: boolean; icon?: ReactNode; badge?: ReactNode };

export function MenuLinks({ entries, onNavigate }: { entries: readonly MenuEntry[]; onNavigate: () => void }) {
  return (
    <ul className="kv-menu-list">
      {entries.map((entry) => (
        <li key={entry.href}>
          <Link href={entry.href} className="kv-menu-link" aria-current={entry.current ? "page" : undefined} onClick={onNavigate}>
            {entry.icon}
            <span className="min-w-0 truncate">{entry.label}</span>
            {entry.badge}
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function MenuGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="kv-menu-group" aria-label={label}>
      <p className="kicker">{label}</p>
      {children}
    </section>
  );
}

export function MenuSheet({ count = 0, children }: { count?: number; children: (close: () => void) => ReactNode }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const pathname = usePathname();
  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <>
      <button type="button" className="kv-bar-menu" aria-haspopup="dialog" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen(true)} data-testid="menu-button">
        <Menu aria-hidden />
        {MENU_LABEL}
        <ControlCount count={count} />
      </button>
      <Sheet open={open} onClose={close} label={MENU_LABEL} panelId={panelId}>
        <div className="mb-2 flex items-center justify-between gap-3 ps-3">
          <p className="kv-panel-head">{MENU_LABEL}</p>
          <button type="button" className="kv-close" onClick={close} aria-label="Close the menu">
            <X aria-hidden />
          </button>
        </div>
        {children(close)}
      </Sheet>
    </>
  );
}
