export function GeneratedCode({ id, html }: { id: string; html: string }) {
  return (
    <pre
      id={id}
      className="max-h-80 min-w-0 max-w-full overflow-auto rounded-md border border-line-200 bg-surface-50 p-3 font-mono text-xs leading-5 text-ink-700"
      tabIndex={0}
      aria-label="Code"
      data-testid="generated-code"
    >
      <code>{html}</code>
    </pre>
  );
}
