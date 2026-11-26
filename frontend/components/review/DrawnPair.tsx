import type { DrawnPicture, DrawnSide } from "@/lib/pageProposalContract";
import { SIDE_TITLES, type PicturePair } from "@/lib/pageProposalView";

export function DrawnPair({ pair, empty }: { pair: PicturePair; empty: Record<DrawnSide, string> }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2" data-testid="drawn-pair" data-pair={pair.key}>
      <DrawnSidePicture side="BEFORE" caption={pair.caption} picture={pair.before} empty={empty.BEFORE} />
      <DrawnSidePicture side="AFTER" caption={pair.caption} picture={pair.after} empty={empty.AFTER} />
    </div>
  );
}

function DrawnSidePicture({ side, caption, picture, empty }: { side: DrawnSide; caption: string; picture: DrawnPicture | null; empty: string }) {
  return (
    <figure className="grid content-start gap-2" data-side={side}>
      {picture ? (
        <a href={picture.url} target="_blank" rel="noopener" className="block">
          <>
            {/* eslint-disable-next-line @next/next/no-img-element -- a private JPEG the API serves at its drawn size, nothing for next/image to optimise */}
            <img
              src={picture.url}
              alt={`${SIDE_TITLES[side]}: ${picture.caption}`}
              width={picture.width}
              height={picture.height}
              loading="lazy"
              decoding="async"
              className="h-auto w-full rounded-plate border border-rule bg-sunk"
            />
          </>
        </a>
      ) : (
        <p className="grid min-h-target place-items-center rounded-plate bg-sunk p-4 font-ui text-label text-ink-2">{empty}</p>
      )}
      <figcaption className="font-ui text-label text-ink-2">
        <span className="font-semibold text-ink-1">{SIDE_TITLES[side]}</span> · {caption}
      </figcaption>
    </figure>
  );
}
