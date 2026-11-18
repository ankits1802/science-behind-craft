"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { MouseEvent, ReactNode } from "react";

import { buttonLook, type ButtonVariant } from "@/components/ui/button";
import { signInHref } from "@/lib/sessionReturn";

export function SignInLink({ next, variant = "primary", children = "Sign in" }: { next?: string; variant?: ButtonVariant; children?: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const open = (event: MouseEvent<HTMLAnchorElement>) => {
    if (next || event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    event.preventDefault();
    router.push(signInHref(`${window.location.pathname}${window.location.search}`));
  };
  return (
    <Link href={signInHref(next ?? pathname)} onClick={open} {...buttonLook({ variant, size: "sm" })} data-testid="sign-in-link">
      {children}
    </Link>
  );
}
