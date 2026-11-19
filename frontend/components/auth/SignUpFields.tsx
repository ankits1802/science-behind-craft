"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { Field, FieldBlock, TextInput } from "@/components/FormControls";
import { Dropdown } from "@/components/ui/Dropdown";
import { roleLabel } from "@/lib/permissions";
import { REQUESTABLE_ROLES } from "@/lib/signUp";
import type { UserRole } from "@/lib/types";

const ROLE_OPTIONS = REQUESTABLE_ROLES.map((value) => ({ value, label: roleLabel(value) }));

export function SignUpFields({ role, onRole }: { role: UserRole; onRole: (role: UserRole) => void }) {
  return (
    <>
      <Field label="Full name">
        <TextInput name="name" required autoComplete="name" maxLength={120} />
      </Field>
      <Field label="Email">
        <TextInput name="email" type="email" required autoComplete="email" placeholder="you@institution.ac.in" />
      </Field>
      <Field label="Institution">
        <TextInput name="affiliation" required={role !== "ARTISAN"} autoComplete="organization" maxLength={200} />
      </Field>
      <FieldBlock label="I am a">
        <Dropdown value={role} onChange={(next) => onRole(next as UserRole)} options={ROLE_OPTIONS} searchable={false} advanceOnSelect={false} />
      </FieldBlock>
      {role !== "STUDENT" && role !== "ARTISAN" ? (
        <Field label="Profile page">
          <TextInput name="profileUrl" type="url" inputMode="url" placeholder="https://" />
        </Field>
      ) : null}
    </>
  );
}

function Pledge({ id, checked, onChange, children }: { id: string; checked: boolean; onChange: (checked: boolean) => void; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <input id={id} type="checkbox" required checked={checked} onChange={(event) => onChange(event.target.checked)} className="mt-1 h-4 w-4 shrink-0 accent-indigo" />
      <span className="font-ui text-ui text-ink-1">{children}</span>
    </div>
  );
}

export function SignUpPromises({ role, adult, onAdult, agreed, onAgreed }: { role: UserRole; adult: boolean; onAdult: (value: boolean) => void; agreed: boolean; onAgreed: (value: boolean) => void }) {
  return (
    <div className="grid gap-3">
      <Pledge id="signup-adult" checked={adult} onChange={onAdult}>
        <label htmlFor="signup-adult">{role === "STUDENT" ? "I am 18 or older, or I am under 18 and my parent or guardian agrees" : "I am 18 or older"}</label>
      </Pledge>
      <Pledge id="signup-agree" checked={agreed} onChange={onAgreed}>
        <label htmlFor="signup-agree">I agree to the</label>{" "}
        <Link href="/privacy" target="_blank" rel="noopener noreferrer" className="kv-link">
          privacy notice
        </Link>
      </Pledge>
    </div>
  );
}
