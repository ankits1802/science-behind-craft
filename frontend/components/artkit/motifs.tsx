import type { KitMotif } from "@/lib/artKit";

import { paint } from "./kitIds";

export function starPoints(cx: number, cy: number, outer: number, inner: number): string {
  return Array.from({ length: 16 }, (_, at) => {
    const radius = at % 2 === 0 ? outer : inner;
    const angle = (Math.PI * at) / 8 - Math.PI / 2;
    return `${(cx + radius * Math.cos(angle)).toFixed(2)},${(cy + radius * Math.sin(angle)).toFixed(2)}`;
  }).join(" ");
}

function MotifTile({ motif, colour }: { motif: KitMotif; colour: string }) {
  if (motif === "star") {
    return (
      <>
        <path d="M0 12 L12 0 L24 12 L12 24 Z" fill="none" stroke={colour} strokeWidth="1" />
        <polygon points={starPoints(12, 12, 7.5, 3.2)} fill={colour} />
        <circle cx="0" cy="0" r="1.6" fill={colour} />
        <circle cx="24" cy="24" r="1.6" fill={colour} />
        <circle cx="24" cy="0" r="1.6" fill={colour} />
        <circle cx="0" cy="24" r="1.6" fill={colour} />
      </>
    );
  }
  if (motif === "lattice") return <path d="M0 0 L24 24 M24 0 L0 24 M-12 12 L12 -12 M12 36 L36 12" fill="none" stroke={colour} strokeWidth="1.6" />;
  if (motif === "dots") {
    return (
      <>
        <circle cx="6" cy="6" r="2.4" fill={colour} />
        <circle cx="18" cy="18" r="2.4" fill={colour} />
      </>
    );
  }
  return <path d="M0 6 H24 M0 18 H24" fill="none" stroke={colour} strokeWidth="2" />;
}

export function MotifPattern({ id, motif, material, size = 24 }: { id: string; motif: KitMotif; material: string; size?: number }) {
  const scale = size / 24;
  return (
    <pattern id={id} width="24" height="24" patternUnits="userSpaceOnUse" patternTransform={scale === 1 ? undefined : `scale(${scale})`}>
      <MotifTile motif={motif} colour={paint(material)} />
    </pattern>
  );
}
