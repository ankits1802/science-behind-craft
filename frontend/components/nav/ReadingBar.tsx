"use client";

import { usePathname } from "next/navigation";

import { SignInLink } from "@/components/auth/SignInLink";
import { Appbar, AppNav, currentHref } from "@/components/nav/Appbar";
import { MenuLinks, MenuSheet } from "@/components/nav/MenuSheet";

export const READING_LINKS = [
  { href: "/crafts", label: "Crafts" },
  { href: "/map", label: "Map" },
  { href: "/compare", label: "Compare" }
] as const;

export function ReadingBar({ signIn }: { signIn: boolean }) {
  const pathname = usePathname();
  const current = currentHref(READING_LINKS.map((link) => link.href), pathname);
  const links = READING_LINKS.map((link) => ({ href: link.href, label: link.label, current: link.href === current }));
  return (
    <Appbar brandHref="/" brand="compact">
      <div className="kv-bar-end" data-testid="reading-bar">
        <AppNav links={links} />
        {signIn ? <SignInLink variant="quiet" /> : null}
        <MenuSheet>{(close) => <MenuLinks entries={links} onNavigate={close} />}</MenuSheet>
      </div>
    </Appbar>
  );
}
