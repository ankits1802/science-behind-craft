export function BrandMark({ className, tile = true }: { className?: string; tile?: boolean }) {
  return (
    <svg viewBox="0 0 108 108" className={className} aria-hidden focusable="false">
      {tile ? <rect width="108" height="108" rx="24" fill="#FAF9F5" /> : null}
      <path d="M44 22h20v6h-4v20l20 32a6 6 0 0 1-5 9H33a6 6 0 0 1-5-9l20-32V28h-4z" fill="#CC785C" />
      <path d="M36 72h36l6 9a2 2 0 0 1-2 3H32a2 2 0 0 1-2-3z" fill="#181715" />
      <circle cx="50" cy="62" r="3.5" fill="#FAF9F5" />
      <circle cx="59" cy="55" r="2.5" fill="#FAF9F5" />
    </svg>
  );
}
