import type { PageChange } from "@/lib/pageProposalContract";
import { CHANGE_KIND_WORDS, MARK_WORDS } from "@/lib/pageProposalView";

export function PageChangeLines({ changes }: { changes: readonly PageChange[] }) {
  if (!changes.length) return null;
  return (
    <ul className="grid gap-3" data-testid="page-change-lines">
      {changes.map((change) => (
        <li
          key={`${change.kind}-${change.change}-${change.ref}`}
          data-change={change.change}
          className={`grid gap-1 border-s-2 border-ink-1 ps-3 ${change.change === "REMOVED" ? "border-dashed" : ""}`}
        >
          <p className="kicker">
            {MARK_WORDS[change.change]} · {CHANGE_KIND_WORDS[change.kind]}
            {change.movedFrom ? ` · moved from ${change.movedFrom}` : ""}
          </p>
          {change.before ? (
            <p className="max-w-measure font-reading text-body-sm text-ink-3 line-through">
              <span className="sr-only">Before: </span>
              {change.before}
            </p>
          ) : null}
          {change.after ? (
            <p className="max-w-measure font-reading text-body-sm text-ink-1">
              <mark className="bg-turmeric-wash text-ink-1">
                <span className="sr-only">After: </span>
                {change.after}
              </mark>
            </p>
          ) : null}
          {change.kind !== "SENTENCE" ? <p className="font-code text-caption text-ink-3">{change.ref}</p> : null}
        </li>
      ))}
    </ul>
  );
}
