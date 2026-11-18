"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { SignInLink } from "@/components/auth/SignInLink";
import { BRAND_NAME, BrandMark } from "@/components/BrandMark";
import { cn } from "@/lib/utils";

export const READING_LINKS = [
  { href: "/crafts", label: "Crafts", wide: false },
  { href: "/map", label: "Map", wide: false },
  { href: "/compare", label: "Compare", wide: true }
] as const;

export function ReadingBar({ signIn }: { signIn: boolean }) {
  const pathname = usePathname();
  const current = (href: string) => pathname === href || pathname.startsWith(`${href}/`);
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-rule bg-ground/95 backdrop-blur" data-testid="reading-bar">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4">
        <Link href="/" className="flex min-w-0 items-center gap-2 text-ink-1">
          <BrandMark className="h-7 w-7 shrink-0" />
          <span className="truncate font-ui text-ui-lg font-semibold">{BRAND_NAME}</span>
        </Link>
        <nav aria-label="Primary" className="ms-auto flex items-center gap-4 text-ui">
          {READING_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={current(link.href) ? "page" : undefined}
              className={cn("kv-link", link.wide && "max-sm:hidden")}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        {signIn ? <SignInLink /> : null}
      </div>
    </header>
  );
}
