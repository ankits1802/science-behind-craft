import { apiFetch } from "@/lib/api";
import type { UserRole } from "@/lib/types";

export const REQUESTABLE_ROLES: readonly UserRole[] = ["STUDENT", "RESEARCHER", "PROFESSOR"];

export type SignUpBody = {
  name: string;
  email: string;
  affiliation: string;
  requestedRole: UserRole;
  profileUrl?: string | null;
  note?: string | null;
  ageAttested: boolean;
  privacyNoticeVersion: string | null;
  turnstileToken?: string | null;
};

export type SignUpAnswer = { status: "EMAIL_SENT"; email: string };

export function requestAccess(body: SignUpBody): Promise<SignUpAnswer> {
  return apiFetch<SignUpAnswer>("/auth/signup", { method: "POST", body: JSON.stringify(body) }, { redirectOn401: false });
}

export type SignUpConfig = {
  signUpOpen: boolean;
  turnstileRequired: boolean;
  turnstileSiteKey: string | null;
};

export function fetchSignUpConfig(): Promise<SignUpConfig> {
  return apiFetch<SignUpConfig>("/auth/config", {}, { redirectOn401: false });
}

export type PrivacyNotice = { version: string; title: string; body: string; publishedAt: string | null };

export function fetchPrivacyNotice(): Promise<PrivacyNotice> {
  return apiFetch<PrivacyNotice>("/privacy/notice", {}, { redirectOn401: false });
}
