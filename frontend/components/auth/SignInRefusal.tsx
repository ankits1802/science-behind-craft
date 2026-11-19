import { FormAlert } from "@/components/auth/FormAlert";
import { accessRefusalChrome, type AccessRefusalKind } from "@/lib/accessRoster";
import { signInHintHeading, type SignInHint } from "@/lib/signIn";

export function SignInRefusal({ kind, hint, message }: { kind: AccessRefusalKind | null; hint: SignInHint; message: string }) {
  const chrome = kind ? accessRefusalChrome(kind) : null;
  const hintHeading = signInHintHeading(hint);
  if (hintHeading) {
    return (
      <FormAlert tone="info" title={hintHeading} className="mb-5">
        {message}
      </FormAlert>
    );
  }

  if (!chrome) return <FormAlert className="mb-5">{message}</FormAlert>;

  const waiting = chrome.tone === "waiting";
  return (
    <FormAlert tone={waiting ? "info" : "error"} title={chrome.heading} className="mb-5" testId={`access-${waiting ? "pending" : "refused"}`}>
      <p className="m-0">{message}</p>
      <p className="m-0 mt-1 text-label text-ink-2">{chrome.advice}</p>
    </FormAlert>
  );
}
