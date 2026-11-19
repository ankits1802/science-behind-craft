import { PlatePicture } from "@/components/editorial/Plate";
import { TextLink } from "@/components/ui/TextLink";

export const HERO_PICTURE = {
  src: "/landing/ajrakh-print-detail-indigo-ground.jpg",
  mask: "/landing/hero-dyed-mask.webp",
  width: 1280,
  height: 960,
  alt: "Detail of an ajrakh print: dark eight-pointed stars and white-outlined motifs on an indigo ground.",
  author: "SMarndi",
  licence: "CC BY-SA 4.0",
  page: "https://commons.wikimedia.org/wiki/File:Ajrak_Print_6.jpg"
} as const;

export const HERO_SPECIMEN = { kicker: "Specimen", family: "Textiles · Hand block printing", name: "Kutch Ajrakh" } as const;

export function HeroCredit() {
  return (
    <>
      Photo:{" "}
      <TextLink href={HERO_PICTURE.page} external className="font-normal text-inherit">
        {`${HERO_PICTURE.author}, ${HERO_PICTURE.licence}, via Wikimedia Commons`}
      </TextLink>
    </>
  );
}

export function HeroPhoto({ priority = false }: { priority?: boolean }) {
  return <PlatePicture alt={HERO_PICTURE.alt} sources={{ src: HERO_PICTURE.src, largest: HERO_PICTURE.src }} priority={priority} className="kv-hero-photo" />;
}
