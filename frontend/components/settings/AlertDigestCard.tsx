"use client";

import { useEffect, useState } from "react";
import { Mail } from "lucide-react";

import { Toggle } from "@/components/ui/Toggle";
import { apiErrorMessage, apiFetch } from "@/lib/api";
import { PREFERENCES_PATH } from "@/lib/preferences";
import { digestChoice, type DigestChoice } from "@/lib/savedView";

const SAVE_FAILED = "Couldn't change the weekly email. Try again.";

export function AlertDigestCard() {
  const [choice, setChoice] = useState<DigestChoice | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch<unknown>(PREFERENCES_PATH)
      .then((raw) => {
        if (!cancelled) setChoice(digestChoice(raw));
      })
      .catch(() => {
        if (!cancelled) setChoice(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!choice?.offered) return null;

  async function change(next: boolean) {
    setBusy(true);
    setError(null);
    try {
      setChoice(digestChoice(await apiFetch<unknown>(PREFERENCES_PATH, { method: "PUT", body: JSON.stringify({ alertDigest: next }) })));
    } catch (cause) {
      setError(apiErrorMessage(cause, SAVE_FAILED));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel flex h-full flex-col gap-3 p-5" data-testid="alert-digest">
      <div className="flex items-center gap-2.5">
        <span className="grid h-8 w-8 place-items-center rounded-md bg-purple-950 text-purple-100">
          <Mail className="h-4 w-4" aria-hidden />
        </span>
        <h2 className="font-display font-bold text-ink-900">Updates</h2>
      </div>
      <Toggle label="Weekly email" description="When a saved answer gets better." checked={choice.on} busy={busy} onChange={(next) => void change(next)} />
      {error ? (
        <p role="alert" className="text-sm text-error-600">
          {error}
        </p>
      ) : null}
    </section>
  );
}
