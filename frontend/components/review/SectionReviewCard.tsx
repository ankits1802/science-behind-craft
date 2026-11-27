import { FactChecks } from "@/components/review/FactEvidence";
import { QueueDecisionBar } from "@/components/review/QueueDecisionBar";
import { QueueItemHeader } from "@/components/review/QueueItemHeader";
import { TextLink } from "@/components/ui/TextLink";
import type { QueueAction, SectionItem } from "@/lib/reviewQueueContract";
import type { ReviewedSentence } from "@/lib/sectionReviewContract";
import { NO_PUBLISHED, PROPOSED_TITLE, publishedTitle, sectionActions, sectionCheckLines, sectionHeadline, sectionWritesLine } from "@/lib/sectionReviewView";

type Decide = (action: QueueAction, words: string) => Promise<string | null>;

export function SectionReviewCard({ item, onDecide }: { item: SectionItem; onDecide: Decide }) {
  const review = item.section;
  return (
    <article className="grid gap-4" data-testid="section-review-card">
      <QueueItemHeader item={item} />
      <div className="grid max-w-measure gap-1">
        <h3 className="font-headline text-h3 text-ink-1">{sectionHeadline(review)}</h3>
        <p className="font-ui text-label text-ink-2">
          <TextLink href={review.pageUrl}>{review.subjectName}</TextLink>
        </p>
        {review.note ? <p className="font-reading text-body-sm text-ink-1">{review.note}</p> : null}
      </div>
      <div className="grid gap-5 md:grid-cols-2">
        <Sentences title={PROPOSED_TITLE} sentences={review.proposed} empty={null} />
        <Sentences title={publishedTitle(review)} sentences={review.published} empty={NO_PUBLISHED} />
      </div>
      {review.checks.length ? <FactChecks gates={sectionCheckLines(review.checks)} /> : null}
      <p className="max-w-measure font-ui text-ui text-ink-1">{sectionWritesLine(review)}</p>
      <QueueDecisionBar actions={sectionActions(review)} onDecide={onDecide} />
    </article>
  );
}

function Sentences({ title, sentences, empty }: { title: string; sentences: ReviewedSentence[]; empty: string | null }) {
  return (
    <section className="grid content-start gap-2">
      <h4 className="font-ui text-h4 text-ink-1">{title}</h4>
      {sentences.length ? (
        <ol className="grid gap-3">
          {sentences.map((sentence, index) => (
            <li key={`${index}-${sentence.text}`} className="grid gap-1">
              <p className="font-reading text-body-sm text-ink-1">{sentence.text}</p>
              <ul className="grid gap-1 border-s-2 border-rule ps-3">
                {sentence.facts.map((fact) => (
                  <li key={fact.id} className="font-ui text-label text-ink-2">
                    {fact.text}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      ) : (
        <p className="font-ui text-label text-ink-2">{empty}</p>
      )}
    </section>
  );
}
