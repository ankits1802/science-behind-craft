import type { CSSProperties, ReactNode } from "react";

import { pictureSources, PlatePicture } from "@/components/editorial/Plate";
import { SpecimenLabel, type SpecimenLabelProps } from "@/components/editorial/SpecimenLabel";
import { TypographicPlate, type PlateMaterial } from "@/components/editorial/TypographicPlate";
import { focalPosition, focalViewBox, type FocalBox } from "@/lib/commonsPicture";

export type MastheadPicture = {
  src: string;
  alt: string;
  caption: ReactNode;
  credit: ReactNode;
  wide?: FocalBox;
  narrow?: FocalBox;
  originalWidth?: number;
};

export type MastheadProps = {
  label: Omit<SpecimenLabelProps, "variant" | "onPhoto">;
  picture?: MastheadPicture | null;
  material: PlateMaterial;
  plateKicker?: string | null;
};

function focalVariables(picture: MastheadPicture): CSSProperties {
  const variables: Record<string, string> = {};
  if (picture.narrow) Object.assign(variables, { "--focal-narrow-at": focalPosition(picture.narrow), "--focal-narrow-box": focalViewBox(picture.narrow) });
  if (picture.wide) Object.assign(variables, { "--focal-wide-at": focalPosition(picture.wide), "--focal-wide-box": focalViewBox(picture.wide) });
  return variables as CSSProperties;
}

export function Masthead({ label, picture, material, plateKicker }: MastheadProps) {
  return (
    <header data-testid="masthead">
      <div className="kv-masthead" data-photo={picture ? "" : undefined} style={picture ? focalVariables(picture) : undefined}>
        {picture ? (
          <PlatePicture alt={picture.alt} sources={pictureSources(picture.src, "masthead", picture.originalWidth)} priority className="kv-masthead-picture" />
        ) : (
          <TypographicPlate material={material} englishName={label.name} nativeName={label.nativeName} kicker={plateKicker} size="masthead" decorative className="kv-masthead-picture" />
        )}
        <SpecimenLabel {...label} variant="masthead" />
      </div>
      {picture ? (
        <div className="mt-3 lg:ms-auto lg:max-w-[46%]">
          <p className="kv-caption">{picture.caption}</p>
          <p className="kv-credit">{picture.credit}</p>
        </div>
      ) : null}
    </header>
  );
}
