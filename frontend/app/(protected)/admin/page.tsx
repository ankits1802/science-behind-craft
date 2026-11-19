"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, BarChart3, KeyRound, Route, ShieldCheck, SlidersHorizontal, UserCog, type LucideIcon } from "lucide-react";

import { ReviewSwitchCard } from "@/components/admin/ReviewSwitchCard";
import { SiteBuildCard } from "@/components/admin/SiteBuildCard";
import { useAuth } from "@/components/AuthProvider";
import { riseItem, staggerParent } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { usePendingAccessCount } from "@/components/hooks/usePendingAccessCount";
import { PageHeader } from "@/components/PageHeader";
import { canAccessRoute, canManageAccessRoster, canManageRouting } from "@/lib/permissions";

type HubCard = {
  href: string;
  title: string;
  note: string;
  icon: LucideIcon;
};

const CARDS: HubCard[] = [
  { href: "/admin/access", title: "Who may sign in", note: "Approve requests and add addresses.", icon: ShieldCheck },
  { href: "/admin/users", title: "Manage users", note: "Change roles, suspend accounts.", icon: UserCog },
  { href: "/admin/keys", title: "API keys", note: "Set and test provider keys.", icon: KeyRound },
  { href: "/admin/routing", title: "AI routing", note: "Model order for each task.", icon: Route },
  { href: "/admin/usage", title: "Usage", note: "Calls, tokens and spend.", icon: BarChart3 }
];

export default function SettingsHubPage() {
  const { user } = useAuth();
  const reduce = useAppReducedMotion();
  const visible = CARDS.filter((card) => canAccessRoute(user, card.href));
  const pending = usePendingAccessCount(canManageAccessRoster(user));
  const description = canManageRouting(user) ? "Accounts, keys and model routing." : "Accounts, access and usage.";

  return (
    <>
      <PageHeader title="Settings hub" description={description} icon={<SlidersHorizontal className="h-5 w-5" aria-hidden />} />
      <motion.ul variants={staggerParent(reduce)} initial="hidden" animate="show" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {visible.map((card) => (
          <motion.li key={card.href} variants={riseItem(reduce)}>
            <Link href={card.href} className="panel group flex h-full items-start gap-4 p-5 transition hover:border-purple-300">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-purple-950 text-purple-100">
                <card.icon className="h-5 w-5" aria-hidden />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2 font-display text-base font-bold text-ink-900">
                  {card.title}
                  {card.href === "/admin/access" && pending && pending.pending > 0 ? (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">{pending.pending} waiting</span>
                  ) : null}
                </span>
                <span className="mt-1 block text-sm leading-6 text-ink-500">{card.note}</span>
              </span>
              <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-ink-300 transition group-hover:text-purple-700" aria-hidden />
            </Link>
          </motion.li>
        ))}
      </motion.ul>
      <ReviewSwitchCard />
      <SiteBuildCard />
    </>
  );
}
