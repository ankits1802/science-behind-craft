export function RequiredMark({ when }: { when: boolean | undefined }) {
  if (when !== true) return null;
  return <span className="font-normal text-ink-3"> (required)</span>;
}
