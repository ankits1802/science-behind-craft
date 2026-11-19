"use client";

import { choosableScope } from "@/lib/oauthConsent";
import type { McpScope, ScopeChoice } from "@/lib/oauthContract";

export function ScopeChoices({
  choices,
  chosen,
  disabled,
  onChange
}: {
  choices: ScopeChoice[];
  chosen: readonly McpScope[];
  disabled: boolean;
  onChange: (scope: McpScope, on: boolean) => void;
}) {
  return (
    <fieldset className="grid gap-3 border-t border-rule pt-5" data-testid="scope-choices">
      <legend className="text-h3 font-reading text-ink-1">What it may do</legend>
      {choices.map((choice) => {
        const id = `scope-${choice.scope}`;
        const open = choosableScope(choice);
        return (
          <div key={choice.scope} className="flex items-start gap-3">
            <input
              id={id}
              type="checkbox"
              className="mt-1.5 h-4 w-4 shrink-0"
              checked={chosen.includes(choice.scope)}
              disabled={disabled || !open}
              aria-describedby={`${id}-about`}
              onChange={(event) => onChange(choice.scope, event.target.checked)}
            />
            <div className="grid gap-0.5">
              <label htmlFor={id} className="text-ui font-ui font-semibold text-ink-1">
                {choice.title}
              </label>
              <p id={`${id}-about`} className="text-body-sm font-reading text-ink-2">
                {choice.description}
                {choice.needs ? <span className="block text-label font-ui text-ink-3">{choice.needs}</span> : null}
              </p>
            </div>
          </div>
        );
      })}
    </fieldset>
  );
}
