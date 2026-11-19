import { PlateGround, type PlateMaterial } from "@/components/editorial/TypographicPlate";
import { cn } from "@/lib/utils";

export function FamilySwatch({ material, className }: { material: PlateMaterial; className?: string }) {
  return (
    <span aria-hidden className={cn("kv-plate block shrink-0", `g-${material}`, className)} data-testid="family-swatch">
      <PlateGround material={material} />
    </span>
  );
}
