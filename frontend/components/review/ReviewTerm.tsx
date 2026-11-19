export function ReviewTerm({ term, value }: { term: string; value: string }) {
  return (
    <div className="grid gap-0.5">
      <dt className="text-ink-3">{term}</dt>
      <dd className="text-ink-1 [overflow-wrap:anywhere]">{value}</dd>
    </div>
  );
}
