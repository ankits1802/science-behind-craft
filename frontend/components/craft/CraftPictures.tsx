"use client";

import { useState } from "react";

import { PictureView } from "@/components/answer/ImageStrip";
import { ClaimChips } from "@/components/craft/CraftClaims";
import type { PagePicture } from "@/lib/craftPageContract";

const LAYOUT = { page: "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4", stage: "grid-cols-2 lg:grid-cols-3" } as const;

function CraftPicture({ picture }: { picture: PagePicture }) {
  const [broken, setBroken] = useState(false);
  if (broken) return null;
  const caption = picture.media.display === "LINK_CARD" && picture.caption === picture.media.title ? null : picture.caption;
  return (
    <li className="grid min-w-0 content-start gap-1.5" data-testid="craft-picture">
      <PictureView media={picture.media} onBroken={() => setBroken(true)} />
      {caption || picture.claimIds.length > 0 ? (
        <p className="text-xs leading-5 text-ink-700 [overflow-wrap:anywhere]">
          {caption}
          {picture.claimIds.length > 0 ? <ClaimChips ids={picture.claimIds} /> : null}
        </p>
      ) : null}
    </li>
  );
}

export function CraftPictures({ pictures, layout = "page" }: { pictures: readonly PagePicture[]; layout?: keyof typeof LAYOUT }) {
  if (pictures.length === 0) return null;
  return (
    <ul className={`grid gap-3 ${LAYOUT[layout]}`} aria-label="Pictures" data-testid="craft-pictures">
      {pictures.map((picture) => (
        <CraftPicture key={picture.media.id} picture={picture} />
      ))}
    </ul>
  );
}
