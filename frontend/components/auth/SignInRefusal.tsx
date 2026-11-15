import { accessRefusalChrome, type AccessRefusalKind } from "@/lib/accessRoster";
import { signInHintHeading, type SignInHint } from "@/lib/signIn";
import { cn } from "@/lib/utils";

export function SignInRefusal({ kind, hint, message }: { kind: AccessRefusalKind | null; hint: SignInHint; message: string }) {
  const chrome = kind ? accessRefusalChrome(kind) : null;
  const hintHeading = signInHintHeading(hint);
  if (hintHeading) {
    return (
      <div role="alert" className="mb-4 grid gap-1.5 rounded-md border border-amber-500/40 bg-amber-100 px-3 py-3 text-sm text-amber-800">
        <p className="font-display text-base font-bold leading-snug">{hintHeading}</p>
        <p className="leading-6">{message}</p>
      </div>
    );
  }

  if (!chrome) {
    return (
      <div role="alert" className="mb-4 rounded-md border border-red-200 bg-error-100 px-3 py-2 text-sm text-error-600">
        {message}
      </div>
    );
  }

  const waiting = chrome.tone === "waiting";
  return (
    <div
      role="alert"
      data-testid={`access-${waiting ? "pending" : "refused"}`}
      className={cn(
        "mb-4 grid gap-1.5 rounded-md border px-3 py-3 text-sm",
        waiting ? "border-amber-500/40 bg-amber-100 text-amber-800" : "border-red-200 bg-error-100 text-error-600"
      )}
    >
      <p className="font-display text-base font-bold leading-snug">{chrome.heading}</p>
      <p className="leading-6">{message}</p>
      <p className="text-xs leading-5">{chrome.advice}</p>
    </div>
  );
}
