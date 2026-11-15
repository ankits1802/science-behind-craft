import { apiFetch } from "@/lib/api";
import type { AccessStatus } from "@/lib/accessRoster";
import type { UserRole } from "@/lib/types";

export const REQUESTABLE_ROLES: readonly UserRole[] = ["STUDENT", "RESEARCHER", "PROFESSOR"];

export type SignUpBody = {
  name: string;
  email: string;
  password: string;
  affiliation: string;
  requestedRole: UserRole;
  profileUrl?: string | null;
  note?: string | null;
  privacyNoticeVersion: string | null;
};

export type SignUpAnswer = { status: AccessStatus; email: string };

export function requestAccess(body: SignUpBody): Promise<SignUpAnswer> {
  return apiFetch<SignUpAnswer>("/auth/signup", { method: "POST", body: JSON.stringify(body) }, { redirectOn401: false });
}

export type PrivacyNotice = { version: string; title: string; body: string; publishedAt: string | null };

export function fetchPrivacyNotice(): Promise<PrivacyNotice> {
  return apiFetch<PrivacyNotice>("/privacy/notice", {}, { redirectOn401: false });
}
