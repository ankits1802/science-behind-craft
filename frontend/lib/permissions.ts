import type { User, UserRole } from "@/lib/types";

export const ROLE_RANK: Record<UserRole, number> = {
  STUDENT: 15,
  RESEARCHER: 30,
  PROFESSOR: 40,
  MASTER_ADMIN: 60
};

export const ROLE_LABELS: Record<UserRole, string> = {
  STUDENT: "Student",
  RESEARCHER: "Researcher",
  PROFESSOR: "Professor",
  MASTER_ADMIN: "Master Admin"
};

export const ROLES_BY_RANK: UserRole[] = (Object.keys(ROLE_RANK) as UserRole[]).sort(
  (a, b) => ROLE_RANK[b] - ROLE_RANK[a]
);

export function roleRank(userOrRole: User | UserRole | null | undefined): number {
  if (!userOrRole) return 0;
  const role = typeof userOrRole === "string" ? userOrRole : userOrRole.role;
  return ROLE_RANK[role] ?? 0;
}

export function roleLabel(role: string | null | undefined): string {
  return ROLE_LABELS[role as UserRole] ?? String(role ?? "");
}

export function hasRank(user: User | null | undefined, role: UserRole): boolean {
  return roleRank(user) >= ROLE_RANK[role];
}

export function isMasterAdmin(user: User | null | undefined) {
  return user?.role === "MASTER_ADMIN";
}

export function isAdmin(user: User | null | undefined) {
  return isMasterAdmin(user);
}

export function isContentAdmin(user: User | null | undefined) {
  return isMasterAdmin(user);
}

export function assignableRoles(user: User | null | undefined): UserRole[] {
  if (isMasterAdmin(user)) return ROLES_BY_RANK;
  if (hasRank(user, "PROFESSOR")) return ROLES_BY_RANK.filter((role) => ROLE_RANK[role] < ROLE_RANK.PROFESSOR);
  return [];
}

export function canManageUser(user: User | null | undefined, target: User): boolean {
  if (isMasterAdmin(user)) return target.role !== "MASTER_ADMIN" || target.id === user?.id;
  return roleRank(target) < roleRank(user);
}

export function canManageUsers(user: User | null | undefined) {
  return hasRank(user, "PROFESSOR");
}

export function canChangeRoles(user: User | null | undefined) {
  return isMasterAdmin(user);
}

export function canSuspendUsers(user: User | null | undefined) {
  return isMasterAdmin(user);
}

export const ACCOUNT_PROVISIONER_ROLES: readonly UserRole[] = ["MASTER_ADMIN"];

export function canProvisionAccounts(user: User | null | undefined) {
  return !!user && ACCOUNT_PROVISIONER_ROLES.includes(user.role);
}

export function provisionableRoles(user: User | null | undefined): UserRole[] {
  if (!canProvisionAccounts(user)) return [];
  const own = roleRank(user);
  return ROLES_BY_RANK.filter((role) => ROLE_RANK[role] < own);
}

export function canManageAccessRoster(user: User | null | undefined) {
  return hasRank(user, "PROFESSOR");
}

export function canAskDeep(user: User | null | undefined) {
  return hasRank(user, "RESEARCHER");
}

export function canManageSecrets(user: User | null | undefined) {
  return isMasterAdmin(user);
}

export function canManageRouting(user: User | null | undefined) {
  return isMasterAdmin(user);
}

export function canReadUsage(user: User | null | undefined) {
  return isMasterAdmin(user);
}

export type RouteGuard = {
  path: string;
  can: (user: User | null | undefined) => boolean;
  gate: string;
  title: string;
  message: string;
};

const MASTER_ADMIN_GUARD = {
  can: isMasterAdmin,
  gate: "require_master_admin",
  title: "Master admin access required",
  message: "Master admins only."
} as const;

const PROFESSOR_GUARD = {
  can: canManageUsers,
  gate: "require_professor",
  title: "Professor access required",
  message: "Needs Professor access or above."
} as const;

export const ROUTE_GUARDS: RouteGuard[] = [
  { path: "/admin", ...MASTER_ADMIN_GUARD },
  { path: "/admin/keys", ...MASTER_ADMIN_GUARD },
  { path: "/admin/routing", ...MASTER_ADMIN_GUARD },
  { path: "/admin/usage", ...MASTER_ADMIN_GUARD },
  { path: "/admin/users", ...PROFESSOR_GUARD },
  { path: "/admin/access", ...PROFESSOR_GUARD, gate: "require_access_roster_manager" }
];

function routeMatches(rulePath: string, pathname: string): boolean {
  const rule = rulePath.split("/").filter(Boolean);
  const actual = pathname.split("/").filter(Boolean);
  if (actual.length < rule.length) return false;
  return rule.every((segment, index) => segment.startsWith(":") || segment === actual[index]);
}

export function routeGuardFor(pathname: string): RouteGuard | null {
  let best: RouteGuard | null = null;
  for (const guard of ROUTE_GUARDS) {
    if (!routeMatches(guard.path, pathname)) continue;
    if (!best || guard.path.length > best.path.length) best = guard;
  }
  return best;
}

export function canAccessRoute(user: User | null | undefined, pathname: string): boolean {
  const guard = routeGuardFor(pathname);
  return !guard || guard.can(user);
}
