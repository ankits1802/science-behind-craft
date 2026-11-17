"use client";

import { useState } from "react";
import Image from "next/image";
import { ExternalLink } from "lucide-react";

import type { ImagesBlock, MediaRef } from "@/lib/explainerContract";

const STRIP_SIZES = "(min-width: 1024px) 220px, (min-width: 640px) 30vw, 45vw";

function WebPicture({ media, onBroken }: { media: MediaRef; onBroken: () => void }) {
  return <Image src={media.imageUrl} alt={media.alt} fill unoptimized sizes={STRIP_SIZES} referrerPolicy="no-referrer" onError={onBroken} className="object-cover" />;
}

function Credit({ media }: { media: MediaRef }) {
  return (
    <figcaption className="break-words text-[11px] leading-4 text-ink-500">
      {media.author ? <span>{media.author} · </span> : null}
      {media.licence && media.licenceUrl ? (
        <a href={media.licenceUrl} target="_blank" rel="noopener noreferrer" className="underline-offset-2 hover:text-purple-700 hover:underline">
          {media.licence}
        </a>
      ) : (
        <span>{media.licence}</span>
      )}
      <span> · {media.site}</span>
    </figcaption>
  );
}

function InlinePicture({ media, onBroken }: { media: MediaRef; onBroken: () => void }) {
  return (
    <figure className="grid gap-1.5" data-display="INLINE">
      <a href={media.pageUrl} target="_blank" rel="noopener noreferrer" className="relative block aspect-[4/3] overflow-hidden rounded-md border border-line-200 bg-surface-50">
        <WebPicture media={media} onBroken={onBroken} />
        <span className="sr-only">(opens in a new tab)</span>
      </a>
      <Credit media={media} />
    </figure>
  );
}

function PictureLinkCard({ media, onBroken }: { media: MediaRef; onBroken: () => void }) {
  return (
    <a
      href={media.pageUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="grid h-full overflow-hidden rounded-md border border-line-200 bg-card transition hover:border-purple-300"
      data-display="LINK_CARD"
    >
      <span className="relative block aspect-[4/3] bg-surface-50">
        <WebPicture media={media} onBroken={onBroken} />
      </span>
      <span className="grid content-start gap-0.5 p-2.5">
        <span className="line-clamp-2 break-words text-xs font-semibold text-ink-900">{media.title}</span>
        <span className="flex min-w-0 items-center gap-1 text-[11px] text-ink-500">
          <span className="truncate">{media.site}</span>
          <ExternalLink className="h-3 w-3 shrink-0" aria-hidden />
        </span>
        {media.credit ? <span className="break-words text-[11px] leading-4 text-ink-500">{media.credit}</span> : null}
        <span className="sr-only">(opens in a new tab)</span>
      </span>
    </a>
  );
}

function StripItem({ media }: { media: MediaRef }) {
  const [broken, setBroken] = useState(false);
  if (broken) return null;
  const onBroken = () => setBroken(true);
  return <li className="min-w-0">{media.display === "INLINE" ? <InlinePicture media={media} onBroken={onBroken} /> : <PictureLinkCard media={media} onBroken={onBroken} />}</li>;
}

export function ImageStrip({ block }: { block: ImagesBlock }) {
  return (
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4" aria-label="Pictures" data-testid="image-strip">
      {block.items.map((item) => (
        <StripItem key={item.media.id} media={item.media} />
      ))}
    </ul>
  );
}
