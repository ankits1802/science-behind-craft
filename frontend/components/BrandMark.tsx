import { STAR_PATH, WORDMARK_DEVANAGARI_PATH, WORDMARK_LATIN_PATH, WORDMARK_LATIN_VIEWBOX, WORDMARK_RULE, WORDMARK_VIEWBOX } from "@/components/brandOutlines";
import { cn } from "@/lib/utils";

export const BRAND_NAME = "KalaVigyan";
export const BRAND_NAME_DEVANAGARI = "कलाविज्ञान";
export const BRAND_LABEL = `${BRAND_NAME}, ${BRAND_NAME_DEVANAGARI}`;

export type WordmarkScript = "both" | "latin";

export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden focusable="false" data-testid="brand-mark">
      <path fill="currentColor" fillRule="evenodd" d={STAR_PATH} />
    </svg>
  );
}

export function BrandWordmark({ className, script = "both" }: { className?: string; script?: WordmarkScript }) {
  if (script === "latin") {
    return (
      <svg viewBox={WORDMARK_LATIN_VIEWBOX} className={className} aria-hidden focusable="false">
        <path fill="currentColor" d={WORDMARK_LATIN_PATH} />
      </svg>
    );
  }
  return (
    <svg viewBox={WORDMARK_VIEWBOX} className={className} aria-hidden focusable="false">
      <path fill="currentColor" d={WORDMARK_LATIN_PATH} />
      <rect className="kv-wordmark-rule" fill="currentColor" opacity={0.5} x={WORDMARK_RULE.x} y={WORDMARK_RULE.y} width={WORDMARK_RULE.width} height={WORDMARK_RULE.height} />
      <path fill="currentColor" d={WORDMARK_DEVANAGARI_PATH} />
    </svg>
  );
}

export function BrandLockup({ className, compact = false, script = "both" }: { className?: string; compact?: boolean; script?: WordmarkScript }) {
  return (
    <span role="img" aria-label={BRAND_LABEL} className={cn("inline-flex min-w-0 items-center gap-2.5 text-ink-1", className)}>
      <BrandMark className={compact ? "h-6 w-6 shrink-0" : "h-[1.625rem] w-[1.625rem] shrink-0"} />
      <BrandWordmark script={script} className={compact ? "h-[1.6rem] w-auto" : "h-7 w-auto"} />
    </span>
  );
}

export function AppbarLockup({ script = "both" }: { script?: WordmarkScript }) {
  return (
    <span role="img" aria-label={BRAND_LABEL} className="kv-bar-lockup">
      <BrandMark className="kv-bar-mark" />
      <BrandWordmark script={script} className="kv-bar-wordmark" />
    </span>
  );
}
