import type { PieceShape } from "@/lib/artKit";
import type { PiecePart } from "@/lib/componentSpecsKit";

import { url, type PartIds } from "../kitIds";
import { MotifPattern } from "../motifs";
import { INK, INK_FAINT, LinePath, MaterialPath, shaded, type Texture } from "../surfaces";

type Outline = { faces: string[]; texture: Texture; marks?: string };

const OUTLINES: Readonly<Record<PieceShape, Outline>> = {
  lump: { faces: ["M24 86 C12 72 20 46 40 38 C52 33 62 42 74 37 C92 31 108 48 104 66 C102 80 94 94 72 97 C52 99 32 97 24 86 Z"], texture: "speckle" },
  vessel: {
    faces: ["M52 12 H68 L66 22 C66 28 78 32 84 44 C92 58 90 78 78 90 C74 94 70 96 68 98 L70 108 H50 L52 98 C50 96 46 94 42 90 C30 78 28 58 36 44 C42 32 54 28 54 22 Z"],
    texture: "weave",
    marks: "M54 22 H66 M50 98 H70"
  },
  slab: { faces: ["M12 50 H86 V94 H12 Z", "M86 50 L108 32 V76 L86 94 Z", "M12 50 L34 32 H108 L86 50 Z"], texture: "speckle" },
  billet: {
    faces: ["M20 40 H94 C101 40 106 52 106 66 C106 80 101 92 94 92 H20 Z", "M20 40 C13 40 8 52 8 66 C8 80 13 92 20 92 C27 92 32 80 32 66 C32 52 27 40 20 40 Z"],
    texture: "grain",
    marks: "M20 52 C15 52 13 60 13 66 C13 72 15 80 20 80 C25 80 27 72 27 66 C27 60 25 52 20 52 Z"
  },
  sheet: { faces: ["M14 22 H106 V84 L86 104 H14 Z", "M86 104 C88 94 96 86 106 84 Z"], texture: "weave" },
  figure: {
    faces: ["M54 40 C49 43 45 49 44 58 L38 98 C38 104 43 108 60 108 C77 108 82 104 82 98 L76 58 C75 49 71 43 66 40 Z", "M60 12 C67 12 72 17 72 24 C72 31 67 36 60 36 C53 36 48 31 48 24 C48 17 53 12 60 12 Z"],
    texture: "speckle",
    marks: "M45 60 C36 66 32 74 31 84 M75 60 C84 66 88 74 89 84"
  },
  culm: { faces: ["M46 6 H74 V114 H46 Z"], texture: "grain", marks: "M44 38 H76 M44 78 H76 M46 34 C54 40 66 40 74 34 M46 74 C54 80 66 80 74 74" }
};

function Face({ d, part, ids, texture, at }: { d: string; part: PiecePart; ids: PartIds; texture: Texture; at: number }) {
  if (!part.material) return <LinePath d={d} ids={ids} texture={texture} />;
  if (at === 0) return <MaterialPath d={d} material={part.material} ids={ids} texture={texture} />;
  return (
    <>
      <path d={d} fill={shaded(part.material, at === 1 ? 82 : 92)} />
      <path d={d} fill={url(ids[texture])} />
      <path d={d} fill="none" stroke={INK} strokeWidth="1.2" strokeLinejoin="round" />
    </>
  );
}

export function PieceArt({ part, ids }: { part: PiecePart; ids: PartIds }) {
  const outline = OUTLINES[part.shape];
  const inlay = `${ids.part}-inlay`;
  return (
    <g data-kit-part="piece" data-kit-shape={part.shape}>
      {part.inlay ? (
        <defs>
          <MotifPattern id={inlay} motif={part.inlay.motif} material={part.inlay.material} size={14} />
        </defs>
      ) : null}
      {outline.faces.map((d, at) => (
        <Face key={d} d={d} part={part} ids={ids} texture={outline.texture} at={at} />
      ))}
      {part.inlay ? <path d={outline.faces[0]} fill={url(inlay)} stroke={INK} strokeWidth="1.2" /> : null}
      {outline.marks ? <path d={outline.marks} fill="none" stroke={part.material ? INK : INK_FAINT} strokeWidth="1.1" strokeLinecap="round" /> : null}
    </g>
  );
}
