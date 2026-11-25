import { Plate } from "@/components/editorial/Plate";
import { QueueDecisionBar } from "@/components/review/QueueDecisionBar";
import { QueueItemHeader } from "@/components/review/QueueItemHeader";
import { ReviewTerm } from "@/components/review/ReviewTerm";
import { TextLink } from "@/components/ui/TextLink";
import { CHECK_STATE_LABELS, PICTURE_CHECK_ACTIONS, PICTURE_CHECK_OUTCOME, VERDICT_LABELS, verdictByLine } from "@/lib/pictureCheckView";
import type { PictureCheckItem, QueueAction } from "@/lib/reviewQueueContract";

type Decide = (action: QueueAction, words: string) => Promise<string | null>;

export function PictureCheckReviewCard({ item, onDecide }: { item: PictureCheckItem; onDecide: Decide }) {
  const { check } = item;
  const media = check.media;
  return (
    <article className="grid gap-4" data-testid="picture-check-card">
      <QueueItemHeader item={item} />
      <div className="grid gap-4 md:grid-cols-2">
        <Plate src={media.imageUrl} alt={media.alt} caption={media.title} credit={media.credit ?? media.site} role="plate" />
        <div className="grid content-start gap-3">
          <p className="max-w-measure font-reading text-body text-ink-1">{check.fact}</p>
          <dl className="grid gap-2 font-ui text-label">
            <ReviewTerm term="Now" value={CHECK_STATE_LABELS[check.state]} />
          </dl>
          <TextLink href={media.pageUrl} external>
            Open the picture&apos;s page
          </TextLink>
        </div>
      </div>
      <section className="grid gap-2">
        <h4 className="font-ui text-h4 text-ink-1">Looks at the picture</h4>
        <ul className="grid gap-3">
          {check.verdicts.map((verdict, index) => (
            <li key={`${verdict.at}-${index}`} className="grid gap-1">
              <p className="font-ui text-ui text-ink-1">{VERDICT_LABELS[verdict.verdict]}</p>
              {verdict.reason ? <p className="max-w-measure font-reading text-quote italic text-ink-2">{verdict.reason}</p> : null}
              <p className="font-ui text-caption text-ink-3">{verdictByLine(verdict)}</p>
            </li>
          ))}
        </ul>
      </section>
      <p className="max-w-measure font-ui text-ui text-ink-1">{PICTURE_CHECK_OUTCOME}</p>
      <QueueDecisionBar actions={PICTURE_CHECK_ACTIONS} onDecide={onDecide} />
    </article>
  );
}
