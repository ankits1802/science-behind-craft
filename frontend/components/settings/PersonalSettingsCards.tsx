"use client";

import { Accessibility, Monitor, Moon, Palette, Sun } from "lucide-react";

import { useThemePreferences } from "@/components/ThemeProvider";
import { Toggle } from "@/components/ui/Toggle";
import type { Preferences, ThemeChoice } from "@/lib/preferences";

const THEME_OPTIONS: Array<{ value: ThemeChoice; label: string; Icon: typeof Monitor }> = [
  { value: "system", label: "Match my device", Icon: Monitor },
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon }
];

const ACCESSIBILITY_OPTIONS: Array<{ key: Exclude<keyof Preferences, "theme" | "answerLanguage">; label: string; helper: string }> = [
  { key: "reducedMotion", label: "Reduce motion", helper: "Adds to your device's own setting." },
  { key: "largerText", label: "Larger text", helper: "About a tenth larger." },
  { key: "highContrast", label: "High contrast", helper: "Stronger borders and focus ring." }
];

function CardHeading({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="grid h-8 w-8 place-items-center rounded-md bg-purple-950 text-purple-100">{icon}</span>
      <h2 className="font-display font-bold text-ink-900">{title}</h2>
    </div>
  );
}

export function AppearanceCard() {
  const { preferences, resolvedTheme, update } = useThemePreferences();

  return (
    <section className="panel flex h-full flex-col p-5">
      <CardHeading icon={<Palette className="h-4 w-4" aria-hidden />} title="Appearance" />
      {preferences.theme === "system" ? <p className="mt-1.5 text-xs leading-5 text-ink-500">Your device is {resolvedTheme} now.</p> : null}
      <div className="mt-3 grid gap-2" role="radiogroup" aria-label="Theme">
        {THEME_OPTIONS.map((option) => {
          const active = preferences.theme === option.value;
          return (
            <label
              key={option.value}
              className={`flex cursor-pointer items-center gap-3 rounded-md border p-3 transition ${
                active ? "border-purple-300 bg-purple-50 dark:bg-purple-950/40" : "border-line-200 bg-card hover:border-purple-300"
              }`}
            >
              <input
                checked={active}
                className="accent-purple-700"
                name="theme"
                onChange={() => update({ theme: option.value })}
                type="radio"
                value={option.value}
              />
              <option.Icon className="h-4 w-4 text-purple-700 dark:text-purple-300" aria-hidden />
              <span className="text-sm font-medium text-ink-900">{option.label}</span>
            </label>
          );
        })}
      </div>
    </section>
  );
}

export function AccessibilityCard() {
  const { preferences, update, saving, error } = useThemePreferences();

  return (
    <section className="panel flex h-full flex-col p-5">
      <CardHeading icon={<Accessibility className="h-4 w-4" aria-hidden />} title="Accessibility" />
      <div className="mt-3 grid gap-1">
        {ACCESSIBILITY_OPTIONS.map((option) => (
          <Toggle
            key={option.key}
            label={option.label}
            description={option.helper}
            checked={preferences[option.key]}
            onChange={(next) => update({ [option.key]: next })}
          />
        ))}
      </div>
      <p className="mt-auto pt-4 text-xs leading-5 text-ink-500" role="status">
        {error ?? (saving ? "Saving…" : "Saved")}
      </p>
    </section>
  );
}
