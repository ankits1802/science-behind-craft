"use client";

import { ToggleSwitch } from "@/components/ui/Toggle";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from "framer-motion";
import {
  BarChart3,
  BookOpen,
  Eye,
  EyeOff,
  KeyRound,
  LogOut,
  MapPinned,
  Menu as MenuIcon,
  MessageCircleQuestion,
  Route,
  Settings as SettingsIcon,
  ShieldCheck,
  SlidersHorizontal,
  UserCog,
  X,
  type LucideIcon
} from "lucide-react";

import { useAdminView } from "@/components/AdminViewProvider";
import { AppSearchHeader } from "@/components/nav/AppSearchHeader";
import { BottomIslandNav } from "@/components/nav/BottomIslandNav";
import { useAuth } from "@/components/AuthProvider";
import { BrandMark } from "@/components/BrandMark";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { usePendingAccessCount } from "@/components/hooks/usePendingAccessCount";
import { HoveredLink, MenuItem } from "@/components/ui/navbar-menu";
import {
  canManageAccessRoster,
  canManageRouting,
  canManageSecrets,
  canManageUsers,
  canReadUsage,
  isAdmin,
  isMasterAdmin,
  roleLabel
} from "@/lib/permissions";
import { lockPageScroll, unlockPageScroll } from "@/lib/scrollLock";
import { cn } from "@/lib/utils";
import type { User } from "@/lib/types";

export const NAV_GROUPS = ["Admin", "Account"] as const;
type NavGroup = (typeof NAV_GROUPS)[number];

const PENDING_ACCESS_BADGE_HREF = "/admin/access";

function PendingAccessBadge({ count }: { count: number }) {
  if (count <= 0) return null;
  const people = count === 1 ? "person is" : "people are";
  return (
    <span
      title={`${count} ${people} waiting to be approved to sign in`}
      className="ml-auto inline-flex shrink-0 items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800"
    >
      {count}
      <span className="font-medium">waiting</span>
      <span className="sr-only">to be approved to sign in</span>
    </span>
  );
}

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  group: NavGroup | null;
  can: (user: User) => boolean;
  gate: string;
  adminSurface?: boolean;
};

const everyone = () => true;

export const NAV_ITEMS: NavItem[] = [
  { href: "/ask", label: "Ask", icon: MessageCircleQuestion, group: null, can: everyone, gate: "get_current_user" },
  { href: "/crafts", label: "Crafts", icon: BookOpen, group: null, can: everyone, gate: "get_current_user" },
  { href: "/map", label: "Map", icon: MapPinned, group: null, can: everyone, gate: "get_current_user" },

  { href: "/admin", label: "Settings hub", icon: SlidersHorizontal, group: "Admin", can: isMasterAdmin, gate: "require_master_admin", adminSurface: true },
  { href: "/admin/access", label: "Who may sign in", icon: ShieldCheck, group: "Admin", can: canManageAccessRoster, gate: "require_access_roster_manager", adminSurface: true },
  { href: "/admin/users", label: "Manage users", icon: UserCog, group: "Admin", can: canManageUsers, gate: "require_professor", adminSurface: true },
  { href: "/admin/keys", label: "API keys", icon: KeyRound, group: "Admin", can: canManageSecrets, gate: "require_master_admin", adminSurface: true },
  { href: "/admin/routing", label: "AI routing", icon: Route, group: "Admin", can: canManageRouting, gate: "require_master_admin", adminSurface: true },
  { href: "/admin/usage", label: "Usage", icon: BarChart3, group: "Admin", can: canReadUsage, gate: "require_master_admin", adminSurface: true },

  { href: "/settings", label: "Settings", icon: SettingsIcon, group: "Account", can: everyone, gate: "get_current_user" }
];

export function isNavItemVisible(item: NavItem, user: User | null | undefined, adminMode: boolean): boolean {
  if (!user || !item.can(user)) return false;
  if (item.adminSurface && isAdmin(user)) return adminMode;
  return true;
}

const spring = { type: "spring" as const, stiffness: 260, damping: 30 };

const NO_MOTION = { duration: 0 } as const;

export function DynamicIslandNav() {
  const { user, logout } = useAuth();
  const adminView = useAdminView();
  const { adminMode, canAdmin, toggleAdminView } = adminView;
  const adminAvailable = (adminView as { available?: boolean }).available ?? canAdmin;
  const router = useRouter();
  const pathname = usePathname();
  const [active, setActive] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [compact, setCompact] = useState(false);
  const { scrollY } = useScroll();
  const sheetRef = useRef<HTMLDivElement | null>(null);
  const menuButtonRef = useRef<HTMLButtonElement | null>(null);
  const sheetOpenerRef = useRef<HTMLButtonElement | null>(null);
  const reduce = useAppReducedMotion();
  const islandTransition = reduce ? NO_MOTION : spring;

  useMotionValueEvent(scrollY, "change", (latest) => {
    const previous = scrollY.getPrevious() ?? 0;
    if (latest < 24) setCompact(false);
    else if (latest > previous + 2) setCompact(true);
    else if (latest < previous - 2) setCompact(false);
  });

  useEffect(() => {
    setSheetOpen(false);
    setActive(null);
  }, [pathname]);

  const closeSheet = useCallback(() => {
    setSheetOpen(false);
    (sheetOpenerRef.current ?? menuButtonRef.current)?.focus();
  }, []);

  const toggleSheetFrom = useCallback((button: HTMLButtonElement) => {
    sheetOpenerRef.current = button;
    setSheetOpen((value) => !value);
  }, []);

  useEffect(() => {
    if (!sheetOpen) return;
    lockPageScroll();
    return unlockPageScroll;
  }, [sheetOpen]);

  useEffect(() => {
    if (!sheetOpen) return;
    const panel = sheetRef.current;
    if (!panel) return;

    const focusable = () =>
      Array.from(
        panel.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')
      );

    focusable()[0]?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeSheet();
        return;
      }
      if (event.key !== "Tab") return;
      const stops = focusable();
      if (stops.length === 0) return;
      const first = stops[0];
      const last = stops[stops.length - 1];
      const focused = document.activeElement as HTMLElement | null;
      const outside = !focused || !panel.contains(focused);
      if (event.shiftKey && (outside || focused === first)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (outside || focused === last)) {
        event.preventDefault();
        first.focus();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [closeSheet, sheetOpen]);

  const visibleItems = useMemo(
    () => NAV_ITEMS.filter((item) => isNavItemVisible(item, user, adminMode)),
    [user, adminMode]
  );
  const rootItems = visibleItems.filter((item) => item.group === null);
  const visibleGroups = NAV_GROUPS.map((label) => ({
    label,
    items: visibleItems.filter((item) => item.group === label)
  })).filter((group) => group.items.length > 0);

  const hubEntryVisible = visibleItems.some((item) => item.href === PENDING_ACCESS_BADGE_HREF);
  const pendingAccess = usePendingAccessCount(hubEntryVisible && canManageAccessRoster(user));
  const pendingAccessCount = pendingAccess?.pending ?? 0;


  if (!user) return null;

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  let activeBase: string | null = null;
  for (const item of visibleItems) {
    const base = item.href.split("?")[0];
    if (pathname !== base && !pathname.startsWith(`${base}/`)) continue;
    if (!activeBase || base.length > activeBase.length) activeBase = base;
  }

  const isActivePath = (href: string) => href.split("?")[0] === activeBase;

  const islandEntry = (item: NavItem) => ({
    label: item.label,
    href: item.href,
    icon: item.icon,
    badge: item.href === PENDING_ACCESS_BADGE_HREF ? pendingAccessCount : 0
  });
  const islandRoots = rootItems.map(islandEntry);
  const islandGroups = visibleGroups.map((group) => ({ label: group.label, entries: group.items.map(islandEntry) }));
  const currentLabel = visibleItems.find((item) => isActivePath(item.href))?.label ?? null;

  return (
    <>
      <div className="nav-island-frame pointer-events-none fixed inset-x-0 top-3 z-50 flex justify-center max-lg:hidden">
        <motion.header
          layout
          transition={islandTransition}
          onMouseLeave={() => setActive(null)}
          className={cn(
            "pointer-events-auto flex items-center gap-1 rounded-full border border-line-200 bg-card/85 shadow-island backdrop-blur-xl",
            compact ? "px-3 py-1.5" : "px-4 py-2"
          )}
        >
          <motion.div
            key={compact ? "brand-compact" : "brand-full"}
            initial={reduce ? { x: 0, opacity: 1 } : { x: -32, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={islandTransition}
          >
            <Link href="/ask" className="flex min-w-fit items-center gap-2 pr-2 text-ink-900">
              <BrandMark className={cn("rounded-lg", compact ? "h-7 w-7" : "h-8 w-8")} />
              <span className={cn("whitespace-nowrap font-display font-bold tracking-tight", compact ? "text-sm" : "text-base")}>
                KalaVigyan
              </span>
            </Link>
          </motion.div>

          <AnimatePresence initial={false}>
            {!compact ? (
              <motion.nav
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={reduce ? NO_MOTION : { duration: 0.22, ease: "easeOut" }}
                className="hidden items-center gap-5 overflow-visible whitespace-nowrap pl-2 pr-1 lg:flex"
                aria-label="Primary"
              >
                {rootItems.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={isActivePath(item.href) ? "page" : undefined}
                    className={cn(
                      "text-sm font-medium transition",
                      isActivePath(item.href) ? "text-purple-700" : "text-ink-700 hover:text-ink-900"
                    )}
                  >
                    {item.label}
                  </Link>
                ))}
                {visibleGroups.map((group) => (
                  <MenuItem key={group.label} setActive={setActive} active={active} item={group.label}>
                    <div className="flex flex-col space-y-3 text-sm">
                      {group.items.map((item) => (
                        <HoveredLink key={item.href} href={item.href}>
                          <span className="inline-flex items-center gap-2">
                            <item.icon className="h-3.5 w-3.5 text-ink-300" aria-hidden />
                            {item.label}
                            {item.href === PENDING_ACCESS_BADGE_HREF ? (
                              <PendingAccessBadge count={pendingAccessCount} />
                            ) : null}
                          </span>
                        </HoveredLink>
                      ))}
                    </div>
                  </MenuItem>
                ))}
              </motion.nav>
            ) : null}
          </AnimatePresence>

          <div className="ml-1 flex items-center gap-1.5">
            {adminAvailable && !compact ? (
              <span
                data-testid="island-admin-view"
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-xs font-medium transition",
                  adminMode ? "border-purple-300 bg-purple-50 text-purple-700" : "border-line-200 bg-card text-ink-500"
                )}
              >
                {adminMode ? <Eye className="h-3.5 w-3.5" aria-hidden /> : <EyeOff className="h-3.5 w-3.5" aria-hidden />}
                <ToggleSwitch
                  label="Admin view"
                  showLabel
                  checked={adminMode}
                  onChange={() => toggleAdminView()}
                  className="min-h-0! gap-1.5 px-0 [&>span:last-child]:-mx-1.5 [&>span:last-child]:-my-[3.5px] [&>span:last-child]:scale-75"
                />
              </span>
            ) : null}
            <button
              ref={menuButtonRef}
              type="button"
              onClick={(event) => toggleSheetFrom(event.currentTarget)}
              aria-label="Toggle navigation menu"
              aria-expanded={sheetOpen}
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-line-200 bg-card text-ink-900 transition hover:bg-surface-50 pointer-coarse:h-11 pointer-coarse:w-11"
            >
              {sheetOpen ? <X className="h-4 w-4" aria-hidden /> : <MenuIcon className="h-4 w-4" aria-hidden />}
            </button>
          </div>
        </motion.header>
      </div>

      <AnimatePresence>
        {sheetOpen ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={reduce ? NO_MOTION : { duration: 0.18 }}
            className="nav-sheet-overlay fixed inset-0 z-90"
          >
            <div
              aria-hidden
              onClick={closeSheet}
              style={{ touchAction: "none" }}
              className="absolute inset-0 bg-ink-900/20 backdrop-blur-xs"
            />
            <motion.div
              ref={sheetRef}
              role="dialog"
              aria-modal="true"
              aria-label="Navigation"
              initial={reduce ? { y: 0, opacity: 0 } : { y: -16, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={reduce ? { y: 0, opacity: 0 } : { y: -16, opacity: 0 }}
              transition={islandTransition}
              className="nav-sheet relative mx-auto w-[min(680px,92vw)] rounded-xl border border-line-200 bg-card shadow-lg"
            >
              <div className="grid gap-1 sm:grid-cols-2">
                {visibleItems.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setSheetOpen(false)}
                    aria-current={isActivePath(item.href) ? "page" : undefined}
                    className={cn(
                      "inline-flex items-center gap-2.5 rounded-md px-3 py-2.5 text-sm font-medium transition",
                      isActivePath(item.href) ? "bg-purple-50 text-purple-700" : "text-ink-700 hover:bg-surface-50 hover:text-ink-900"
                    )}
                  >
                    <item.icon className="h-4 w-4 shrink-0 text-ink-300" aria-hidden />
                    {item.label}
                    {item.href === PENDING_ACCESS_BADGE_HREF ? <PendingAccessBadge count={pendingAccessCount} /> : null}
                  </Link>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line-200 pt-4">
                {adminAvailable ? (
                  <ToggleSwitch label="Admin view" showLabel checked={adminMode} onChange={() => toggleAdminView()} />
                ) : null}
                <div className="ml-auto text-right text-xs">
                  <div className="font-medium text-ink-900">{user.name}</div>
                  <div className="text-ink-500">{roleLabel(user.role)}</div>
                </div>
                <button onClick={handleLogout} data-danger className="field-danger">
                  <LogOut className="h-4 w-4" aria-hidden />
                  Logout
                </button>
              </div>
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <AppSearchHeader
        appName={APP_NAME}
        logo={(className) => <BrandMark className={className} />}
        onOpenSearch={() => router.push("/crafts")}
        searchOpen={false}
      />
      <BottomIslandNav
        roots={islandRoots}
        groups={islandGroups}
        currentLabel={currentLabel}
        onOpenMenu={toggleSheetFrom}
        menuOpen={sheetOpen}
        hidden={false}
      />
    </>
  );
}

const APP_NAME = "KalaVigyan";
