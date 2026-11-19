import Link from "next/link";

import { TypographicPlate } from "@/components/editorial/TypographicPlate";
import type { AtlasPlate } from "@/lib/atlasCollection";
import type { NativeName } from "@/lib/editorialText";
import { cn } from "@/lib/utils";

export function PlateTags({ plate }: { plate: Pick<AtlasPlate, "monograph" | "gi"> }) {
  if (!plate.monograph && !plate.gi) return null;
  return (
    <span className="inline-flex flex-wrap justify-end gap-1">
      {plate.monograph ? <span className="rounded-plate border border-current px-[5px] py-px font-ui text-caption font-medium text-ink-1">Monograph</span> : null}
      {plate.gi ? (
        <span className="rounded-plate border border-current px-[5px] py-px font-ui text-caption font-semibold tracking-[0.04em] text-ink-2">
          GI<span className="sr-only"> registered</span>
        </span>
      ) : null}
    </span>
  );
}

function PlateStrip({ plate }: { plate: AtlasPlate }) {
  return (
    <>
      <span className="font-reading text-figcaption font-medium group-hover:text-indigo group-hover:underline group-hover:decoration-1 group-hover:underline-offset-3">{plate.craft.displayName}</span>
      <span className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1 font-ui text-caption text-ink-3">
        <span>{plate.state}</span>
        <PlateTags plate={plate} />
      </span>
    </>
  );
}

export function CollectionPlate({ plate, nativeName = null, lead = false, className }: { plate: AtlasPlate; nativeName?: NativeName | null; lead?: boolean; className?: string }) {
  return (
    <Link href={plate.href} className={cn("group block min-w-0 rounded-plate", className)} data-testid="collection-plate" data-lead={lead || undefined}>
      <TypographicPlate
        material={plate.material}
        englishName={plate.craft.displayName}
        nativeName={nativeName}
        kicker={plate.kicker}
        strip={<PlateStrip plate={plate} />}
        className={cn("h-full", lead ? "sm:min-h-72" : undefined)}
      />
    </Link>
  );
}
