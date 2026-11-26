import { QueueDecisionBar } from "@/components/review/QueueDecisionBar";
import type { PageAction, PageProposalView, PageScope } from "@/lib/pageProposalContract";
import { decides } from "@/lib/pageProposalView";

const PAGE_ACTIONS: PageAction[] = ["approve", "reject"];

export function ScopeDecision({
  view,
  scope,
  title,
  onDecide
}: {
  view: PageProposalView;
  scope: PageScope;
  title: string;
  onDecide: (scope: PageScope, action: PageAction, words: string) => Promise<string | null>;
}) {
  if (!decides(view, scope)) return null;
  return (
    <section className="grid gap-3" data-testid="scope-decision" data-scope={scope.scope}>
      <h5 className="font-ui text-ui font-semibold text-ink-1">{title}</h5>
      <QueueDecisionBar actions={PAGE_ACTIONS} onDecide={(action, words) => onDecide(scope, action as PageAction, words)} />
    </section>
  );
}
