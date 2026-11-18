import { STAR_PATH, WORDMARK_DEVANAGARI_PATH, WORDMARK_LATIN_PATH, WORDMARK_RULE, WORDMARK_VIEWBOX } from "@/components/brandOutlines";
import { cn } from "@/lib/utils";

export const BRAND_NAME = "KalaVigyan";
export const BRAND_NAME_DEVANAGARI = "कलाविज्ञान";

export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden focusable="false" data-testid="brand-mark">
      <path fill="currentColor" fillRule="evenodd" d={STAR_PATH} />
    </svg>
  );
}

export function BrandWordmark({ className }: { className?: string }) {
  return (
    <svg viewBox={WORDMARK_VIEWBOX} className={className} aria-hidden focusable="false">
      <path fill="currentColor" d={WORDMARK_LATIN_PATH} />
      <rect fill="currentColor" opacity={0.5} x={WORDMARK_RULE.x} y={WORDMARK_RULE.y} width={WORDMARK_RULE.width} height={WORDMARK_RULE.height} />
      <path fill="currentColor" d={WORDMARK_DEVANAGARI_PATH} />
    </svg>
  );
}

export function BrandLockup({ className, compact = false }: { className?: string; compact?: boolean }) {
  return (
    <span role="img" aria-label={`${BRAND_NAME}, ${BRAND_NAME_DEVANAGARI}`} className={cn("inline-flex min-w-0 items-center gap-2.5 text-ink-1", className)}>
      <BrandMark className={compact ? "h-6 w-6 shrink-0" : "h-[1.625rem] w-[1.625rem] shrink-0"} />
      <BrandWordmark className={compact ? "h-[1.6rem] w-auto" : "h-7 w-auto"} />
    </span>
  );
}
