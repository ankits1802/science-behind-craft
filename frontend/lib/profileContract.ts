import { apiFetch } from "@/lib/api";
import { INSTANT } from "@/lib/answerShapes";
import { boolean, integer, list, nullable, object, oneOf, parseShape, text, type Shape } from "@/lib/shape";

export const PROFILE_PATH = "/profile/me";
export const STUDENT_PROFILE_PATH = "/profile/me/student";
export const ARTISAN_PROFILE_PATH = "/profile/me/artisan";
export const RECORDING_CONSENT_PATH = "/profile/me/recording-consent";
export const RECORDING_NOTICE_PATH = (language: string) => `/artisan/recording-notice?language=${encodeURIComponent(language)}`;
export const DISTRICTS_PATH = "/places/districts";

export const AGE_BANDS = ["UNDER_14", "14_17", "18_22", "23_PLUS"] as const;
export const GENDERS = ["WOMAN", "MAN", "ANOTHER", "UNSAID"] as const;
export const CREDIT_MODES = ["FULL_NAME", "FIRST_NAME", "CRAFT_AND_DISTRICT"] as const;
export const GUARDIAN_STATES = ["NOT_NEEDED", "NEEDED", "CONFIRMED"] as const;
export const ARTISAN_CRAFTS_MAX = 12;

export type AgeBand = (typeof AGE_BANDS)[number];
export type Gender = (typeof GENDERS)[number];
export type CreditMode = (typeof CREDIT_MODES)[number];

export const AGE_BAND_LABELS: Record<AgeBand, string> = { UNDER_14: "Under 14", "14_17": "14 to 17", "18_22": "18 to 22", "23_PLUS": "23 and over" };
export const GENDER_LABELS: Record<Gender, string> = { WOMAN: "Woman", MAN: "Man", ANOTHER: "Another identity", UNSAID: "Prefer not to say" };
export const CREDIT_LABELS: Record<CreditMode, string> = { FULL_NAME: "Your full name", FIRST_NAME: "Your first name", CRAFT_AND_DISTRICT: "An artisan of your craft and district" };

export type ProfileCraft = { slug: string; name: string; displayName: string; familyLabel: string | null; kindLabel: string | null };
export type ProfileDistrict = { lgd: number; name: string; state: { lgd: number; name: string } };
export type StudentPart = { ageBand: AgeBand | null; gender: Gender | null; guardianConsent: (typeof GUARDIAN_STATES)[number] };
export type ArtisanPart = {
  crafts: ProfileCraft[];
  district: ProfileDistrict | null;
  spokenLanguage: string | null;
  credit: { mode: CreditMode | null; name: string | null; shortName: string | null; preview: string | null };
  recordingConsent: { noticeVersion: string; acceptedAt: string } | null;
  recordingNoticeVersion: string;
};
export type ProfileView = { role: string; profileRequired: boolean; student: StudentPart | null; artisan: ArtisanPart | null; updatedAt: string | null };
export type DistrictList = { states: { lgd: number; name: string; districts: { lgd: number; name: string }[] }[] };
export type RecordingNotice = { version: string; language: string; title: string; body: string; publishedAt: string };
export type ArtisanProfileBody = {
  craftSlugs: string[];
  districtLgd: number;
  spokenLanguage: string;
  adultConfirmed: true;
  credit: { mode: CreditMode; name?: string | null; shortName?: string | null };
};

const craftShape: Shape<ProfileCraft> = object({ slug: text, name: text, displayName: text, familyLabel: nullable(text), kindLabel: nullable(text) });
const districtShape: Shape<ProfileDistrict> = object({ lgd: integer, name: text, state: object({ lgd: integer, name: text }) });

export const profileViewShape: Shape<ProfileView> = object({
  role: text,
  profileRequired: boolean,
  student: nullable(object({ ageBand: nullable(oneOf(AGE_BANDS)), gender: nullable(oneOf(GENDERS)), guardianConsent: oneOf(GUARDIAN_STATES) })),
  artisan: nullable(
    object({
      crafts: list(craftShape),
      district: nullable(districtShape),
      spokenLanguage: nullable(text),
      credit: object({ mode: nullable(oneOf(CREDIT_MODES)), name: nullable(text), shortName: nullable(text), preview: nullable(text) }),
      recordingConsent: nullable(object({ noticeVersion: text, acceptedAt: INSTANT })),
      recordingNoticeVersion: text
    })
  ),
  updatedAt: nullable(INSTANT)
});

export const districtListShape: Shape<DistrictList> = object({
  states: list(object({ lgd: integer, name: text, districts: list(object({ lgd: integer, name: text })) }))
});

export const recordingNoticeShape: Shape<RecordingNotice> = object({ version: text, language: text, title: text, body: text, publishedAt: text });

export function creditPreview(mode: CreditMode, name: string, craft: string, district: ProfileDistrict | null): string {
  const place = district ? `${district.name}, ${district.state.name}` : "";
  const named = mode === "CRAFT_AND_DISTRICT" || !name.trim() ? `An artisan of ${craft}` : `${name.trim()}, ${craft}`;
  return place ? `${named}, ${place}` : named;
}

export function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] ?? "";
}

export async function fetchProfile(): Promise<ProfileView> {
  return parseShape(profileViewShape, await apiFetch<unknown>(PROFILE_PATH));
}

export async function saveStudentProfile(ageBand: AgeBand, gender: Gender): Promise<ProfileView> {
  const raw = await apiFetch<unknown>(STUDENT_PROFILE_PATH, { method: "PUT", body: JSON.stringify({ ageBand, gender }) });
  return parseShape(profileViewShape, raw);
}

export async function saveArtisanProfile(body: ArtisanProfileBody): Promise<ProfileView> {
  return parseShape(profileViewShape, await apiFetch<unknown>(ARTISAN_PROFILE_PATH, { method: "PUT", body: JSON.stringify(body) }));
}

export async function fetchDistricts(): Promise<DistrictList> {
  return parseShape(districtListShape, await apiFetch<unknown>(DISTRICTS_PATH));
}

export async function fetchRecordingNotice(language: string): Promise<RecordingNotice> {
  return parseShape(recordingNoticeShape, await apiFetch<unknown>(RECORDING_NOTICE_PATH(language)));
}

export async function agreeToRecording(noticeVersion: string, language: string): Promise<void> {
  await apiFetch<unknown>(RECORDING_CONSENT_PATH, { method: "POST", body: JSON.stringify({ noticeVersion, language }) });
}

export async function withdrawRecording(): Promise<{ withdrawnContributions: number; deletedConversations: number }> {
  const raw = await apiFetch<unknown>(RECORDING_CONSENT_PATH, { method: "DELETE" });
  return parseShape(object({ withdrawnContributions: integer, deletedConversations: integer }), raw);
}
