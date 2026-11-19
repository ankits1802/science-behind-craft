import type { ReactNode } from "react";

export const LEGACY_SCOPES = ["mb", "chem", "pt", "rm", "sa", "ask"] as const;
export type LegacyScopeName = (typeof LEGACY_SCOPES)[number];

export function LegacyScope({ scope, children }: { scope: LegacyScopeName; children: ReactNode }) {
  return (
    <div className={`bx bx-${scope}`} data-native-view="">
      <div className="screen">{children}</div>
    </div>
  );
}
