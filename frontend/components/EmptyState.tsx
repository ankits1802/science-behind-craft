import type { ReactNode } from "react";

import { ActionGroup } from "@/components/ui/ActionGroup";

export type EmptyStateProps = {
  title: string;
  body?: ReactNode;
  plate?: ReactNode;
  actions?: ReactNode;
  headingLevel?: 2 | 3;
};

export function EmptyState({ title, body, plate, actions, headingLevel = 2 }: EmptyStateProps) {
  const Heading = headingLevel === 2 ? "h2" : "h3";
  return (
    <div className="kv-empty" data-testid="empty-state">
      {plate ? <div className="mb-1 w-30">{plate}</div> : null}
      <Heading className="font-reading text-h3 text-ink-1">{title}</Heading>
      {body ? <p className="max-w-[44ch] font-ui text-ui font-normal text-ink-2">{body}</p> : null}
      {actions ? <ActionGroup className="mt-1.5">{actions}</ActionGroup> : null}
    </div>
  );
}
