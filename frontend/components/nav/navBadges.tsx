import { unreadText } from "@/lib/savedView";

export function waitingText(count: number): string {
  return `${count} ${count === 1 ? "person is" : "people are"} waiting to be approved to sign in`;
}

export function PendingAccessBadge({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span title={waitingText(count)} className="ms-auto inline-flex shrink-0 items-center gap-1 rounded-pill bg-sunk px-2 font-ui text-caption font-semibold leading-5 text-ink-1 tabular-nums">
      {count}
      <span className="font-medium">waiting</span>
      <span className="sr-only">to be approved to sign in</span>
    </span>
  );
}

export function UnreadBadge({ count }: { count: number }) {
  const text = unreadText(count);
  if (!text) return null;
  return (
    <span className="ms-1.5 inline-flex min-w-5 items-center justify-center rounded-pill bg-ink-1 px-1.5 font-ui text-caption font-semibold leading-5 text-ground tabular-nums" data-testid="unread-notes">
      <span aria-hidden>{count > 99 ? "99+" : count}</span>
      <span className="sr-only">{`, ${text}`}</span>
    </span>
  );
}

export function ControlCount({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span className="kv-bar-count" aria-hidden>
      {count > 99 ? "99+" : count}
    </span>
  );
}
