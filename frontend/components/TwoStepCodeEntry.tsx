"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

import { OtpCodeInput, type OtpCodeInputHandle } from "@/components/ui/OtpCodeInput";

export type TwoStepCodeKind = "totp" | "recovery";

export type TwoStepCodeEntryHandle = { focus: () => void };

export const TwoStepCodeEntry = forwardRef<
  TwoStepCodeEntryHandle,
  {
    kind: TwoStepCodeKind;
    onKindChange: (kind: TwoStepCodeKind) => void;
    value: string;
    onChange: (value: string) => void;
    onComplete?: (code: string) => void;
    allowRecovery: boolean;
    totpLabel?: string;
    totpHint?: string;
    error?: boolean;
    errorKey?: number;
    disabled?: boolean;
    autoFocus?: boolean;
    idPrefix: string;
  }
>(function TwoStepCodeEntry(
  {
    kind,
    onKindChange,
    value,
    onChange,
    onComplete,
    allowRecovery,
    totpLabel = "6-digit code from your authenticator app",
    totpHint,
    error = false,
    errorKey = 0,
    disabled = false,
    autoFocus = false,
    idPrefix
  },
  ref
) {
  const otp = useRef<OtpCodeInputHandle | null>(null);
  const recovery = useRef<HTMLInputElement | null>(null);
  const showRecovery = allowRecovery && kind === "recovery";

  const switched = useRef(false);
  useEffect(() => {
    if (!switched.current) {
      switched.current = true;
      return;
    }
    if (showRecovery) recovery.current?.focus();
    else otp.current?.focus();
  }, [showRecovery]);

  useImperativeHandle(ref, () => ({
    focus: () => (showRecovery ? recovery.current?.focus() : otp.current?.focus())
  }));

  return (
    <div className="grid gap-2">
      {showRecovery ? (
        <div className="grid gap-1.5">
          <label htmlFor={`${idPrefix}-recovery`} className="field-label">
            Recovery code
          </label>
          <input
            id={`${idPrefix}-recovery`}
            ref={recovery}
            type="text"
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            maxLength={20}
            placeholder="xxxx-xxxx"
            disabled={disabled}
            aria-invalid={error || undefined}
            aria-describedby={`${idPrefix}-recovery-hint`}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            className="kv-input max-w-64 font-code tracking-[0.15em]"
          />
          <p id={`${idPrefix}-recovery-hint`} className="kv-field-hint">
            One of the recovery codes you saved when you turned this on. Each one works once.
          </p>
        </div>
      ) : (
        <OtpCodeInput
          ref={otp}
          id={`${idPrefix}-otp`}
          label={totpLabel}
          hint={totpHint}
          value={value}
          onChange={onChange}
          onComplete={onComplete}
          error={error}
          errorKey={errorKey}
          disabled={disabled}
          autoFocus={autoFocus}
        />
      )}
      {allowRecovery ? (
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            onChange("");
            onKindChange(showRecovery ? "totp" : "recovery");
          }}
          className="kv-link inline-flex min-h-11 w-fit items-center font-ui text-ui disabled:opacity-60 sm:min-h-9"
        >
          {showRecovery ? "Use your authenticator app instead" : "Use a recovery code instead"}
        </button>
      ) : null}
    </div>
  );
});
