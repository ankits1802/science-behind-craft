import type { FieldChange } from "@/lib/stagedReviewContract";
import { changeValue } from "@/lib/stagedReviewView";

export function StagedChanges({ changes }: { changes: readonly FieldChange[] }) {
  if (!changes.length) return null;
  return (
    <section className="grid gap-2" data-testid="staged-changes">
      <h4 className="font-ui text-h4 text-ink-1">What the edit changes</h4>
      <dl className="grid gap-3 font-ui text-label">
        {changes.map((change) => (
          <div key={change.field} className="grid gap-1">
            <dt className="text-ink-1">{change.field}</dt>
            <dd className="grid gap-0.5 sm:grid-cols-[auto_minmax(0,1fr)] sm:gap-x-4">
              <span className="text-ink-3">Before</span>
              <span className="text-ink-2 [overflow-wrap:anywhere]">{changeValue(change.before)}</span>
              <span className="text-ink-3">After</span>
              <span className="text-ink-1 [overflow-wrap:anywhere]">{changeValue(change.after)}</span>
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
