import type { Picture } from "@/lib/componentSpecsPlates";

export function SpecPicture({ picture, className }: { picture: Picture; className?: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- the approved page's own picture at its built width, which next/image would re-encode
    <img
      className={className}
      src={picture.src}
      width={picture.width}
      height={picture.height}
      alt={picture.alt}
      loading={picture.loading ?? undefined}
      fetchPriority={picture.fetchPriority ?? undefined}
      decoding={picture.decoding ?? undefined}
    />
  );
}
