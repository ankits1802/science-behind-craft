"use client";

import { useState } from "react";

import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { Toggle } from "@/components/ui/Toggle";
import { apiErrorMessage } from "@/lib/api";
import {
  approveItem,
  editItem,
  REJECT_REASON_LABELS,
  rejectItem,
  TESTIMONY_REJECT_REASONS,
  type RejectReason,
  type ReviewItem
} from "@/lib/testimonyContract";

const REASON_OPTIONS = TESTIMONY_REJECT_REASONS.map((value) => ({ value, label: REJECT_REASON_LABELS[value] }));
const SCREEN_LABELS: Record<string, string> = { NAME_HELD_BACK: "Names someone the credit holds back. Edit it first." };

export function ReviewCard({ item, onDecided }: { item: ReviewItem; onDecided: () => void }) {
  const [current, setCurrent] = useState(item);
  const [claimText, setClaimText] = useState(item.claimText ?? "");
  const [english, setEnglish] = useState(item.english ?? "");
  const [checked, setChecked] = useState(item.englishSource !== "MACHINE");
  const [reason, setReason] = useState<RejectReason | "">("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const edited = claimText !== (current.claimText ?? "") || english !== (current.english ?? "");

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (cause) {
      setError(apiErrorMessage(cause, "Couldn't save. Reload it."));
    } finally {
      setBusy(false);
    }
  }

  const saveEdit = () => run(async () => setCurrent(await editItem(current, { claimText, english })));
  const approve = () => run(async () => { await approveItem(current, checked); onDecided(); });
  const reject = () => run(async () => { if (reason) await rejectItem(current, reason, note.trim() || null); onDecided(); });

  return (
    <li className="grid gap-3 rounded-md border border-line-200 bg-card p-4" data-testid="review-card">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
        {current.craft.name} · {current.speaker.district} · {current.locator}
      </p>
      <p className="text-sm text-ink-700">{current.line}</p>
      {current.context.before.text ? <p className="text-sm text-ink-500">Asked: {current.context.before.english ?? current.context.before.text}</p> : null}
      {current.quote ? (
        <p lang={current.language} dir={current.direction} className="text-base text-ink-900">
          “{current.quote}”
        </p>
      ) : null}
      {current.context.audio ? <audio controls preload="none" src={`${current.context.audio.url}#t=${current.context.audio.startMs / 1000},${current.context.audio.endMs / 1000}`} className="w-full" /> : null}
      <label className="grid gap-1">
        <span className="field-label">English</span>
        <textarea value={english} onChange={(event) => setEnglish(event.target.value)} maxLength={600} rows={2} className="field-input" />
      </label>
      <label className="grid gap-1">
        <span className="field-label">Fact</span>
        <textarea value={claimText} onChange={(event) => setClaimText(event.target.value)} maxLength={300} rows={2} className="field-input" />
      </label>
      {current.screens.map((screen) => (
        <p key={screen} role="alert" className="text-sm text-error-600">
          {SCREEN_LABELS[screen] ?? screen}
        </p>
      ))}
      <Toggle label="English checked" checked={checked} onChange={setChecked} disabled={busy} />
      {error ? <p role="alert" className="text-sm text-error-600">{error}</p> : null}
      <ActionGroup align="start">
        {edited ? <Button type="button" variant="outline" disabled={busy} onClick={() => void saveEdit()}>Save edit</Button> : null}
        <Button type="button" disabled={busy || edited || current.screens.length > 0} onClick={() => void approve()}>
          Approve
        </Button>
      </ActionGroup>
      <div className="grid gap-2 sm:grid-cols-[1fr_2fr_auto]">
        <SearchableSelect value={reason} onChange={(next) => setReason(next as RejectReason)} options={REASON_OPTIONS} ariaLabel="Reason" placeholder="Reason" searchable={false} />
        <input value={note} onChange={(event) => setNote(event.target.value)} maxLength={500} placeholder="Note for the artisan" aria-label="Note for the artisan" className="field-input" />
        <Button type="button" variant="outline" disabled={busy || !reason || (reason === "OTHER" && !note.trim())} onClick={() => void reject()}>
          Reject
        </Button>
      </div>
    </li>
  );
}
