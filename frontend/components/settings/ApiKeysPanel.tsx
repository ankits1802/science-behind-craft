"use client";

import { Check, KeyRound, Plus, RotateCw, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { ResizableTh } from "@/components/ResizableTh";
import { RowActions, rowAction } from "@/components/RowActions";
import { OtpCodeInput } from "@/components/ui/OtpCodeInput";
import { isCompleteCode } from "@/components/ui/otpCode";
import { PasswordRevealButton } from "@/components/ui/PasswordReveal";
import { useToast } from "@/components/ui/Toast";
import { apiFetch } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { ActionGroup } from "@/components/ui/ActionGroup";

type SecretSource = "database" | "environment" | "unset";
type SecretStatus = "UNKNOWN" | "OK" | "FAILED";

export type ManagedSecret = {
  key: string;
  label: string;
  description: string;
  configured: boolean;
  source: SecretSource;
  overrideUnreadable?: boolean;
  hint: string | null;
  lastStatus: SecretStatus;
  lastCheckedAt: string | null;
  lastError: string | null;
  updatedBy: string | null;
  updatedAt: string | null;
};

export function hasStoredOverride(secret: Pick<ManagedSecret, "source" | "overrideUnreadable">): boolean {
  return secret.source === "database" || secret.overrideUnreadable === true;
}

const SOURCE_META: Record<SecretSource, { label: string; tone: string; help: string }> = {
  database: {
    label: "Saved here",
    tone: "border-purple-300 bg-purple-50 text-purple-700",
    help: "Saved here — this value overrides the default."
  },
  environment: {
    label: "Default",
    tone: "border-line-200 bg-surface-50 text-ink-700",
    help: "Using the default value. Saving here overrides it."
  },
  unset: {
    label: "Not set",
    tone: "border-amber-500/30 bg-amber-100 text-amber-800",
    help: "No value set — the features that need it are off."
  }
};

const STATUS_META: Record<SecretStatus, { label: string; tone: string }> = {
  OK: { label: "OK", tone: "border-success-600/25 bg-success-100 text-success-600" },
  FAILED: { label: "Failed", tone: "border-error-600/25 bg-error-100 text-red-800" },
  UNKNOWN: { label: "Unknown", tone: "border-line-200 bg-surface-50 text-ink-500" }
};

type Busy = { key: string; action: "test" | "save" | "clear" } | null;

export function ApiKeysPanel() {
  const { toast } = useToast();

  const [secrets, setSecrets] = useState<ManagedSecret[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<Busy>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [revealDraft, setRevealDraft] = useState(false);
  const [confirmingClear, setConfirmingClear] = useState<string | null>(null);
  const [stepCode, setStepCode] = useState("");

  useEffect(() => {
    apiFetch<ManagedSecret[]>("/secrets")
      .then(setSecrets)
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load the managed keys"));
  }, []);

  const replaceRow = useCallback((row: ManagedSecret) => {
    setSecrets((current) => (current ? current.map((item) => (item.key === row.key ? row : item)) : [row]));
  }, []);

  async function test(secret: ManagedSecret) {
    setBusy({ key: secret.key, action: "test" });
    setError(null);
    try {
      const row = await apiFetch<ManagedSecret>(`/secrets/${secret.key}/test`, { method: "POST" });
      replaceRow(row);
      toast({
        title: row.lastStatus === "OK" ? `${row.label} is working` : `${row.label} failed`,
        description: row.lastStatus === "OK" ? "The provider accepted the key." : row.lastError ?? "The provider rejected the key.",
        tone: row.lastStatus === "OK" ? "success" : "error"
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to test that key");
    } finally {
      setBusy(null);
    }
  }

  async function save(secret: ManagedSecret) {
    const value = draft.trim();
    if (!value || !isCompleteCode(stepCode)) return;
    setBusy({ key: secret.key, action: "save" });
    setError(null);
    try {
      const row = await apiFetch<ManagedSecret>(`/secrets/${secret.key}`, {
        method: "PUT",
        body: JSON.stringify({ value, twoFactorCode: stepCode })
      });
      replaceRow(row);
      setEditing(null);
      setDraft("");
      setStepCode("");
      toast({ title: `${row.label} saved`, description: "It is in use for everyone now.", tone: "success" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save that key");
    } finally {
      setBusy(null);
    }
  }

  async function clearOverride(secret: ManagedSecret) {
    if (!isCompleteCode(stepCode)) return;
    setBusy({ key: secret.key, action: "clear" });
    setError(null);
    try {
      const row = await apiFetch<ManagedSecret>(`/secrets/${secret.key}`, {
        method: "DELETE",
        body: JSON.stringify({ twoFactorCode: stepCode })
      });
      replaceRow(row);
      setConfirmingClear(null);
      setStepCode("");
      toast({
        title: `${row.label} override cleared`,
        description:
          row.source === "environment"
            ? "The default value applies again."
            : "This key has no value now.",
        tone: "info"
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to clear that override");
    } finally {
      setBusy(null);
    }
  }

  function startEdit(secret: ManagedSecret) {
    setConfirmingClear(null);
    setEditing(secret.key);
    setDraft("");
    setStepCode("");
  }

  return (
    <div className="grid gap-4">
      <div className="rounded-md border border-purple-300 bg-purple-50 px-4 py-3 text-sm leading-6 text-purple-800">
        Saved keys apply to everyone at once. Saving or clearing one asks for your two-step code.
      </div>

      {error ? <div className="rounded-md border border-red-200 bg-error-100 px-3 py-2 text-sm text-red-800">{error}</div> : null}

      <section className="panel overflow-hidden">
        <div className="border-b border-line-200 px-4 py-3">
          <h2 className="font-display font-bold text-ink-900">Managed API keys</h2>
          <p className="text-sm text-ink-500">Test a key before relying on it.</p>
        </div>

        {!secrets ? (
          <div className="p-4 text-sm text-ink-500">{error ? "Could not load the keys." : "Loading…"}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px] text-left text-sm">
              <thead className="bg-surface-50 text-xs uppercase text-ink-500">
                <tr>
                  <ResizableTh>Key</ResizableTh>
                  <ResizableTh>Value</ResizableTh>
                  <ResizableTh>Source</ResizableTh>
                  <ResizableTh>Status</ResizableTh>
                  <ResizableTh>Last updated</ResizableTh>
                  <ResizableTh className="text-right">Actions</ResizableTh>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-200">
                {secrets.map((secret) => {
                  const source = SOURCE_META[secret.source] ?? SOURCE_META.unset;
                  const status = STATUS_META[secret.lastStatus] ?? STATUS_META.UNKNOWN;
                  const rowBusy = busy?.key === secret.key ? busy.action : null;

                  return (
                    <tr className="align-top" key={secret.key}>
                      <td className="px-4 py-3">
                        <div className="font-medium text-ink-900">{secret.label}</div>
                        <div className="font-mono text-[0.6875rem] uppercase tracking-wide text-ink-500">{secret.key}</div>
                        <p className="mt-1 max-w-sm text-xs leading-5 text-ink-500">{secret.description}</p>
                      </td>

                      <td className="px-4 py-3">
                        <span className="font-mono text-xs text-ink-500">
                          {secret.configured ? `••••••••${secret.hint ?? ""}` : "Not set"}
                        </span>
                      </td>

                      <td className="px-4 py-3">
                        <span className={`inline-block rounded-full border px-2.5 py-1 text-xs font-medium ${source.tone}`}>
                          {source.label}
                        </span>
                        <p className="mt-1 max-w-48 text-[0.6875rem] leading-4 text-ink-500">{source.help}</p>
                        {secret.overrideUnreadable ? (
                          <p className="mt-1 max-w-48 text-[0.6875rem] leading-4 text-error-600">
                            Unreadable, so not in use. Enter it again or clear it.
                          </p>
                        ) : null}
                      </td>

                      <td className="px-4 py-3">
                        <span className={`inline-block rounded-full border px-2.5 py-1 text-xs font-medium ${status.tone}`}>
                          {status.label}
                        </span>
                        <p className="mt-1 text-[0.6875rem] leading-4 text-ink-500">
                          {secret.lastCheckedAt ? `Checked ${formatDateTime(secret.lastCheckedAt)}` : "Never tested"}
                        </p>
                        {secret.lastError ? (
                          <p className="mt-1 max-w-56 text-[0.6875rem] leading-4 text-error-600">{secret.lastError}</p>
                        ) : null}
                      </td>

                      <td className="px-4 py-3 text-ink-700">
                        {secret.updatedAt ? (
                          <>
                            <div className="text-xs">{formatDateTime(secret.updatedAt)}</div>
                            <div className="text-[0.6875rem] text-ink-500">by {secret.updatedBy ?? "unknown"}</div>
                          </>
                        ) : (
                          <span className="text-xs text-ink-500">Never edited here</span>
                        )}
                      </td>

                      <td className="px-4 py-3">
                        <RowActions>
                          <button
                            className={rowAction("neutral")}
                            disabled={rowBusy === "test"}
                            onClick={() => test(secret)}
                            type="button"
                          >
                            <RotateCw className={`h-3.5 w-3.5 ${rowBusy === "test" ? "animate-spin" : ""}`} aria-hidden />
                            {rowBusy === "test" ? "Testing…" : "Test"}
                          </button>
                          <button className={rowAction("edit")} onClick={() => startEdit(secret)} type="button">
                            {secret.source === "unset" ? (
                              <>
                                <Plus className="h-3.5 w-3.5" aria-hidden />
                                Add key
                              </>
                            ) : (
                              <>
                                <KeyRound className="h-3.5 w-3.5" aria-hidden />
                                Update
                              </>
                            )}
                          </button>
                          {hasStoredOverride(secret) ? (
                            <button
                              data-danger className={rowAction("danger")}
                              onClick={() => {
                                setEditing(null);
                                setStepCode("");
                                setConfirmingClear(secret.key);
                              }}
                              type="button"
                            >
                              <Trash2 className="h-3.5 w-3.5" aria-hidden />
                              Clear override
                            </button>
                          ) : null}
                        </RowActions>

                        {editing === secret.key ? (
                          <div className="mt-3 rounded-md border border-purple-300 bg-purple-50 p-3">
                            <label className="grid gap-1">
                              <span className="field-label">
                                {secret.source === "unset" ? `New ${secret.label} key` : `Replace the ${secret.label} key`}
                              </span>
                              <div className="relative">
                                <input
                                  autoComplete="off"
                                  autoFocus
                                  className="field-input pr-10 font-mono text-xs"
                                  onChange={(event) => setDraft(event.target.value)}
                                  onKeyDown={(event) => {
                                    if (event.key === "Enter") {
                                      event.preventDefault();
                                      void save(secret);
                                    }
                                    if (event.key === "Escape") setEditing(null);
                                  }}
                                  placeholder="Paste the key — whitespace is trimmed"
                                  spellCheck={false}
                                  type={revealDraft ? "text" : "password"}
                                  value={draft}
                                />
                                <PasswordRevealButton
                                  revealed={revealDraft}
                                  onToggle={() => setRevealDraft((value) => !value)}
                                  size={16}
                                  noun="key"
                                />
                              </div>
                            </label>
                            <OtpCodeInput
                              className="mt-3"
                              label="Your two-step code"
                              value={stepCode}
                              onChange={setStepCode}
                              disabled={rowBusy === "save"}
                            />
                            <ActionGroup align="end" className="mt-2">
                              <button
                                className={rowAction("neutral")}
                                onClick={() => {
                                  setEditing(null);
                                  setDraft("");
                                }}
                                type="button"
                              >
                                <X className="h-3.5 w-3.5" aria-hidden />
                                Cancel
                              </button>
                              <button
                                className={rowAction("edit")}
                                disabled={!draft.trim() || !isCompleteCode(stepCode) || rowBusy === "save"}
                                onClick={() => save(secret)}
                                type="button"
                              >
                                <Check className="h-3.5 w-3.5" aria-hidden />
                                {rowBusy === "save" ? "Saving…" : "Save key"}
                              </button>
                            </ActionGroup>
                          </div>
                        ) : null}

                        {confirmingClear === secret.key ? (
                          <div className="mt-3 rounded-md border border-red-200 bg-error-100 p-3 text-left">
                            <p className="text-xs font-medium text-error-600">Clear the stored {secret.label} key?</p>
                            <p className="mt-1 text-[0.6875rem] leading-4 text-ink-700">
                              {secret.overrideUnreadable
                                ? "Nothing is using it."
                                : "The default value applies again, if there is one."}
                            </p>
                            <OtpCodeInput
                              className="mt-3"
                              label="Your two-step code"
                              value={stepCode}
                              onChange={setStepCode}
                              disabled={rowBusy === "clear"}
                            />
                            <ActionGroup align="end" className="mt-2">
                              <button className={rowAction("neutral")} onClick={() => setConfirmingClear(null)} type="button">
                                Keep it
                              </button>
                              <button
                                data-danger className={rowAction("danger")}
                                disabled={rowBusy === "clear" || !isCompleteCode(stepCode)}
                                onClick={() => clearOverride(secret)}
                                type="button"
                              >
                                <Trash2 className="h-3.5 w-3.5" aria-hidden />
                                {rowBusy === "clear" ? "Clearing…" : "Clear override"}
                              </button>
                            </ActionGroup>
                          </div>
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
