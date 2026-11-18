"use client";

import { useId, useState } from "react";

import { switchAria, toggleOutcome } from "@/components/ui/toggleKeys";

export type ToggleProps = {
  checked?: boolean;
  defaultChecked?: boolean;
  onChange?: (next: boolean) => void;
  label: string;
  description?: React.ReactNode;
  status?: React.ReactNode;
  disabled?: boolean;
  busy?: boolean;
  busyLabel?: string;
  name?: string;
  id?: string;
  className?: string;
  testId?: string;
};

export function Toggle({
  checked: checkedProp,
  defaultChecked = false,
  onChange,
  label,
  description,
  status,
  disabled = false,
  busy = false,
  busyLabel,
  name,
  id,
  className = "",
  testId
}: ToggleProps) {
  const [inner, setInner] = useState(defaultChecked);
  const checked = checkedProp ?? inner;
  const generated = useId();
  const switchId = id ?? `toggle-${generated}`;
  const labelId = `${switchId}-label`;
  const descriptionId = `${switchId}-description`;
  const statusId = `${switchId}-status`;
  const inert = disabled || busy;

  function flip() {
    const next = toggleOutcome(checked, { disabled, busy });
    if (next === null) return;
    if (checkedProp === undefined) setInner(next);
    onChange?.(next);
  }

  const describedBy = [description ? descriptionId : null, status || (busy && busyLabel) ? statusId : null]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={`flex min-h-target items-center justify-between gap-4 py-2 ${inert ? "" : "cursor-pointer"} ${className}`}
      onClick={(event) => {
        if ((event.target as HTMLElement).closest("button[role=switch]")) return;
        flip();
      }}
    >
      <div className="min-w-0">
        <span id={labelId} className={`block font-ui text-ui ${disabled ? "text-ink-3" : "text-ink-1"}`}>
          {label}
        </span>
        {description ? (
          <div id={descriptionId} className="mt-0.5 font-ui text-label font-normal text-ink-3">
            {description}
          </div>
        ) : null}
        {status || (busy && busyLabel) ? (
          <span id={statusId} className="mt-1 block font-ui text-label text-ink-2" aria-live="polite">
            {busy && busyLabel ? busyLabel : status}
          </span>
        ) : null}
      </div>
      <button
        type="button"
        {...switchAria(checked, busy)}
        id={switchId}
        data-testid={testId}
        aria-labelledby={labelId}
        aria-describedby={describedBy || undefined}
        disabled={disabled}
        onClick={(event) => {
          event.preventDefault();
          flip();
        }}
        className="kv-switch"
      />
      {name && checked ? <input type="hidden" name={name} value="on" /> : null}
    </div>
  );
}

export function ToggleSwitch({
  checked,
  label,
  onChange,
  disabled,
  showLabel = false,
  className = ""
}: {
  checked: boolean;
  label: string;
  onChange: (next: boolean) => void;
  disabled?: boolean;
  showLabel?: boolean;
  className?: string;
}) {
  return (
    <button
      type="button"
      {...switchAria(checked, false)}
      aria-label={showLabel ? undefined : label}
      disabled={disabled}
      onClick={() => {
        const next = toggleOutcome(checked, { disabled });
        if (next !== null) onChange(next);
      }}
      className={`group inline-flex min-h-target shrink-0 items-center gap-2 px-0.5 disabled:cursor-not-allowed disabled:opacity-55 ${className}`}
    >
      {showLabel ? <span className="font-ui text-label text-ink-2">{label}</span> : null}
      <span aria-hidden className="kv-switch" data-checked={checked} />
    </button>
  );
}
