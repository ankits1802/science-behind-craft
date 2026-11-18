import { apiFetch, buildQuery } from "@/lib/api";
import { assignableRoles, canChangeRoles, canConfirmGuardianConsent, canManageUser, canSuspendUsers } from "@/lib/permissions";
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
  return apiFetch<User>(`/users/${encodeURIComponent(userId)}/restore`, { method: "POST" });
}

export const GUARDIAN_STATEMENT_VERSION = "2026-11-18";

export const GUARDIAN_STATEMENT =
  "If this student is under 18, their parent or guardian has agreed to their using KalaVigyan, and our institution holds that agreement.";

export function guardianConsentMissing(user: User): boolean {
  return user.guardianConsent === "NOT_CONFIRMED";
}

export function offersGuardianConfirmation(viewer: User | null | undefined, target: User): boolean {
  return Boolean(viewer) && viewer?.id !== target.id && canConfirmGuardianConsent(viewer) && canManageUser(viewer, target) && guardianConsentMissing(target);
}

export async function confirmGuardianConsent(target: User): Promise<User> {
  await apiFetch<{ userId: string; confirmedAt: string }>(`/users/${encodeURIComponent(target.id)}/guardian-consent`, {
    method: "POST",
    body: JSON.stringify({ affirmed: true, noticeVersion: GUARDIAN_STATEMENT_VERSION })
  });
  return { ...target, guardianConsent: "CONFIRMED" };
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
    resetTwoStep: canSuspendUsers(viewer) && Boolean(target.twoFactorEnabled)
  };
}

export function roleChoices(viewer: User | null | undefined, target: User): UserRole[] {
  const allowed = assignableRoles(viewer);
  return allowed.includes(target.role) ? allowed : [target.role, ...allowed];
}
