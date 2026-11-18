import { shownNativeName, type NativeName } from "@/lib/editorialText";
import { cn } from "@/lib/utils";

export type NameSize = "title" | "h1" | "h2" | "h3";

export type NameElement = "h1" | "h2" | "h3" | "p";

const SIZE_CLASS: Record<NameSize, string> = {
  title: "font-headline text-title",
  h1: "font-headline text-h1",
  h2: "font-headline text-h2",
  h3: "font-headline text-h3 font-[480] leading-[1.1] tracking-[-0.012em]"
};

export function NameStack({
  englishName,
  nativeName,
  size,
  as: Element = "p",
  id,
  className
}: {
  englishName: string;
  nativeName?: NativeName | null;
  size: NameSize;
  as?: NameElement;
  id?: string;
  className?: string;
}) {
  const shown = shownNativeName(nativeName);
  const fit = size === "title" || size === "h1" ? size : undefined;
  return (
    <Element id={id} className={cn("kv-names text-ink-1 [font-variant-numeric:lining-nums]", SIZE_CLASS[size], className)} data-fit={fit} data-testid="name-stack">
      <span className="kv-name">{englishName}</span>
      {shown ? (
        <span lang={shown.lang} data-script={shown.script} dir={shown.dir}>
          {shown.text}
        </span>
      ) : null}
    </Element>
  );
}
