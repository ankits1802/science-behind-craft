import { commonsThumb } from "@/lib/commonsPicture";
import type { Picture } from "@/lib/componentSpecsPlates";

const COMMONS_UPLOAD = "https://upload.wikimedia.org/";
const PLATE_WIDTH = 960;

export function pictureSource(picture: Picture): string {
  return picture.src.startsWith(COMMONS_UPLOAD) ? commonsThumb(picture.src, Math.min(PLATE_WIDTH, picture.width)) : picture.src;
}

export function focalPosition(picture: Picture): string | undefined {
  const focal = picture.focal;
  if (!focal) return undefined;
  const centre = (start: number, size: number) => `${Math.round((start + size / 2) * 1000) / 10}%`;
  return `${centre(focal.x, focal.width)} ${centre(focal.y, focal.height)}`;
}

export function SpecPicture({ picture, className }: { picture: Picture; className?: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- the approved page's own picture at its built width, which next/image would re-encode
    <img
      className={className}
      src={pictureSource(picture)}
      width={picture.width}
      height={picture.height}
      alt={picture.alt}
      loading={picture.loading ?? undefined}
      fetchPriority={picture.fetchPriority ?? undefined}
      decoding={picture.decoding ?? undefined}
      style={picture.focal ? { objectPosition: focalPosition(picture) } : undefined}
    />
  );
}
