import { apiFetch, buildQuery } from "@/lib/api";
import { assignableRoles, canChangeRoles, canManageUser, canSuspendUsers, isMasterAdmin } from "@/lib/permissions";
import type { PageResult, User, UserRole } from "@/lib/types";

export const USERS_PAGE_SIZE = 20;

export type AccountStanding = "ACTIVE" | "SUSPENDED";

export function accountStanding(user: User): AccountStanding {
  return user.suspendedAt || user.isActive === false ? "SUSPENDED" : "ACTIVE";
}

export const STANDING_LABEL: Record<AccountStanding, string> = {
  ACTIVE: "Active",
  SUSPENDED: "Suspended"
};

export function twoStepFact(user: User): string {
  return user.twoFactorEnabled ? "Turned on" : "Not turned on";
}

export function listUsers(params: { search?: string; role?: string; page: number }): Promise<PageResult<User>> {
  return apiFetch<PageResult<User>>(
    `/users${buildQuery({ search: params.search, role: params.role, page: params.page, pageSize: USERS_PAGE_SIZE })}`
  );
}

export function changeUserRole(userId: string, role: UserRole): Promise<User> {
  return apiFetch<User>(`/users/${encodeURIComponent(userId)}`, { method: "PATCH", body: JSON.stringify({ role }) });
}

export function suspendUser(userId: string): Promise<User> {
  return apiFetch<User>(`/users/${encodeURIComponent(userId)}/suspend`, { method: "POST" });
}

export function reactivateUser(userId: string): Promise<User> {
  return apiFetch<User>(`/users/${encodeURIComponent(userId)}/reactivate`, { method: "POST" });
}

export type RowOffers = {
  role: boolean;
  suspend: boolean;
  reactivate: boolean;
  resetTwoStep: boolean;
};

export function rowOffers(viewer: User | null | undefined, target: User): RowOffers {
  if (!viewer || viewer.id === target.id || !canManageUser(viewer, target)) {
    return { role: false, suspend: false, reactivate: false, resetTwoStep: false };
  }
  const suspended = accountStanding(target) === "SUSPENDED";
  return {
    role: canChangeRoles(viewer) && roleChoices(viewer, target).length > 1,
    suspend: canSuspendUsers(viewer) && !suspended,
    reactivate: canSuspendUsers(viewer) && suspended,
    resetTwoStep: isMasterAdmin(viewer) && Boolean(target.twoFactorEnabled)
  };
}

export function roleChoices(viewer: User | null | undefined, target: User): UserRole[] {
  const allowed = assignableRoles(viewer);
  return allowed.includes(target.role) ? allowed : [target.role, ...allowed];
}
