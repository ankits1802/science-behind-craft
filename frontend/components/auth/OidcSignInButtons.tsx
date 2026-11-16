"use client";

import { Button } from "@/components/ui/button";
import type { OidcProvider, OidcProviderId } from "@/lib/oidcSignIn";

function MicrosoftMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 21 21" className={className} aria-hidden>
      <rect x="1" y="1" width="9" height="9" fill="#f25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
      <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
      <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
    </svg>
  );
}

function YahooMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden>
      <path
        d="M0 6.71h4.62l2.69 6.88 2.72-6.88h4.5L7.76 22.5H3.23l1.86-4.32L0 6.71zm17.62 5.05h-5.03L17.06 1.5h5.02l-4.46 10.26zm-3.03 1.4c1.55 0 2.8 1.26 2.8 2.81a2.8 2.8 0 1 1-5.61 0c0-1.55 1.26-2.8 2.81-2.8z"
        fill="#5f01d1"
      />
    </svg>
  );
}

function ProviderMark({ id, className }: { id: OidcProviderId; className?: string }) {
  return id === "MICROSOFT" ? <MicrosoftMark className={className} /> : <YahooMark className={className} />;
}

export function OidcSignInButtons({
  providers,
  disabled,
  onStart
}: {
  providers: OidcProvider[];
  disabled: boolean;
  onStart: (provider: OidcProvider) => void;
}) {
  if (providers.length === 0) return null;
  return (
    <div className="grid gap-2.5">
      {providers.map((provider) => (
        <Button
          key={provider.id}
          type="button"
          variant="provider"
          size="auth"
          disabled={disabled}
          onClick={() => onStart(provider)}
          className="w-full min-w-0"
        >
          <ProviderMark id={provider.id} className="h-5 w-5 shrink-0" />
          <span className="min-w-0 truncate">Continue with {provider.label}</span>
        </Button>
      ))}
    </div>
  );
}
