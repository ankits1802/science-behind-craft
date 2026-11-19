export const PLAY_ICON_MARKUP = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4.5 2.8 L13 8 L4.5 13.2 Z" fill="currentColor"/></svg>';
export const PAUSE_ICON_MARKUP =
  '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3.5" y="2.8" width="3.2" height="10.4" rx=".8" fill="currentColor"/><rect x="9.3" y="2.8" width="3.2" height="10.4" rx=".8" fill="currentColor"/></svg>';

export function PlayIcon() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <path d="M4.5 2.8 L13 8 L4.5 13.2 Z" fill="currentColor" />
    </svg>
  );
}

export function DownloadIcon() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <path d="M8 2 V10.5 M4.5 7 L8 10.5 L11.5 7 M2.5 13.5 H13.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function AiTagIcon() {
  return (
    <svg viewBox="0 0 14 14" aria-hidden="true">
      <rect x="1" y="1" width="12" height="12" rx="2" fill="none" stroke="currentColor" strokeWidth="1.3" />
      <path d="M1.6 12.4 L12.4 1.6" stroke="currentColor" strokeWidth="1.3" />
      <path d="M1 13 L13 13 L13 1 Z" fill="currentColor" fillOpacity=".35" />
    </svg>
  );
}

export function AiTag({ label }: { label: string }) {
  return (
    <span className="ai-tag">
      <AiTagIcon />
      {label}
    </span>
  );
}
