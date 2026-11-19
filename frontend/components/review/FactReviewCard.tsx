import { FactChecks, FactSources } from "@/components/review/FactEvidence";
import { QueueDecisionBar } from "@/components/review/QueueDecisionBar";
import { QueueItemHeader } from "@/components/review/QueueItemHeader";
import { ReviewTerm } from "@/components/review/ReviewTerm";
import type { FactItem, QueueAction } from "@/lib/reviewQueueContract";
import { codeLabel, FACT_STATUS_LABELS, factActions, fieldsLine } from "@/lib/reviewQueueView";

type Decide = (action: QueueAction, words: string) => Promise<string | null>;

export function FactReviewCard({ item, onDecide }: { item: FactItem; onDecide: Decide }) {
  const fact = item.fact;
  const fields = fieldsLine(fact.field, fact.fields);
  return (
    <article className="grid gap-4" data-testid="fact-review-card">
      <QueueItemHeader item={item} />
      <p className="max-w-measure font-reading text-body text-ink-1">{fact.statement}</p>
      <dl className="grid gap-x-6 gap-y-2 font-ui text-label sm:grid-cols-2">
        <ReviewTerm term="Shown now" value={FACT_STATUS_LABELS[fact.status] ?? codeLabel(fact.status)} />
        <ReviewTerm term="Level" value={codeLabel(fact.level)} />
        {fields ? <ReviewTerm term="Field" value={fields} /> : null}
        {fact.concept ? <ReviewTerm term="About" value={`${fact.concept.name} (${codeLabel(fact.concept.type)})`} /> : null}
      </dl>
      {fact.sourcesDiffer ? (
        <p className="max-w-measure border-s-2 border-madder ps-3 font-ui text-ui text-ink-1">
          <span className="text-madder">Sources differ.</span> It disagrees with a fact already held; both are shown with their sources.
        </p>
      ) : null}
      <div className="grid gap-5 md:grid-cols-2">
        <FactSources sources={fact.sources} />
        <FactChecks gates={fact.gates} />
      </div>
      <QueueDecisionBar actions={factActions(fact.status)} onDecide={onDecide} />
    </article>
  );
}
