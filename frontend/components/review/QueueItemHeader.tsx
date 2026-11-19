import { TextLink } from "@/components/ui/TextLink";
import { formatDateTime } from "@/lib/format";
import type { QueueItem } from "@/lib/reviewQueueContract";
import { KIND_NOUNS, ORIGIN_LABELS, proposerLine } from "@/lib/reviewQueueView";

export function QueueItemHeader({ item }: { item: QueueItem }) {
  const proposer = proposerLine(item.proposer);
  return (
    <div className="grid gap-1">
      <p className="kicker">
        {KIND_NOUNS[item.kind]} · {ORIGIN_LABELS[item.origin]}
      </p>
      <p className="font-ui text-label text-ink-3">
        {item.craft ? (
          <>
            <TextLink href={item.craft.path}>{item.craft.name}</TextLink>
            {" · "}
          </>
        ) : null}
        <time dateTime={item.submittedAt}>{formatDateTime(item.submittedAt)}</time>
        {proposer ? ` · ${proposer}` : null}
      </p>
    </div>
  );
}
