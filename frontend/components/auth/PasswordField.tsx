"use client";

import type { ReactNode, Ref } from "react";

import { PasswordRevealButton } from "@/components/ui/PasswordReveal";
import { cn } from "@/lib/utils";

export type PasswordFieldProps = {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: "current-password" | "new-password";
  revealed: boolean;
  onReveal?: () => void;
  minLength?: number;
  maxLength?: number;
  placeholder?: string;
  hint?: ReactNode;
  inputRef?: Ref<HTMLInputElement>;
};

export function PasswordField({ id, label, value, onChange, autoComplete, revealed, onReveal, minLength, maxLength, placeholder, hint, inputRef }: PasswordFieldProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  return (
    <div className="grid min-w-0 gap-1.5">
      <label htmlFor={id} className="field-label">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          ref={inputRef}
          type={revealed ? "text" : "password"}
          autoComplete={autoComplete}
          required
          minLength={minLength}
          maxLength={maxLength}
          placeholder={placeholder}
          value={value}
          aria-describedby={hintId}
          onChange={(event) => onChange(event.target.value)}
          className={cn("kv-input", onReveal && "pe-12")}
        />
        {onReveal ? <PasswordRevealButton revealed={revealed} onToggle={onReveal} size={20} /> : null}
      </div>
      {hint ? (
        <p id={hintId} className="kv-field-hint m-0">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function AuthLinkLine({ children }: { children: ReactNode }) {
  return <p className="mt-6 text-center font-ui text-ui text-ink-2">{children}</p>;
}
