"use client";

import { ClaimChips } from "@/components/craft/CraftClaims";
import { Plate } from "@/components/editorial/Plate";
import { plateClaimIds, type ContributedPlate } from "@/lib/craftContributed";

const LAYOUT = { page: "sm:grid-cols-2 lg:grid-cols-3", stage: "sm:grid-cols-2" } as const;

function ContributedFigure({ plate }: { plate: ContributedPlate }) {
  const claims = plateClaimIds(plate);
  const caption = (
    <>
      {plate.caption}
      {claims.length > 0 ? <ClaimChips ids={claims} /> : null}
    </>
  );
  return (
    <li className="min-w-0" data-testid="contributed-plate" data-origin={plate.origin}>
      <Plate src={plate.url} alt={plate.altText} ratio={`${plate.width} / ${plate.height}`} caption={caption} credit={plate.credit} />
    </li>
  );
}

export function ContributedPlates({ plates, layout = "page" }: { plates: readonly ContributedPlate[]; layout?: keyof typeof LAYOUT }) {
  if (plates.length === 0) return null;
  return (
    <ul className={`grid gap-5 ${LAYOUT[layout]}`} aria-label="Contributed pictures" data-testid="contributed-plates">
      {plates.map((plate) => (
        <ContributedFigure key={plate.contributionId} plate={plate} />
      ))}
    </ul>
  );
}
