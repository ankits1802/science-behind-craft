export type Dye = "cloth" | "harda" | "harda-dry" | "lime" | "kut" | "kesari" | "mud" | "mud-wet" | "leuco" | "indigo" | "indigo-deep" | "madder" | "madder-bright" | "pink";

export type StagePalette = { ground: Dye; motif: Dye; resist: Dye; outline: Dye | null; texture: "threads" | "grit" | null };

export const STAGE_PALETTES: readonly StagePalette[] = [
  { ground: "cloth", motif: "cloth", resist: "cloth", outline: null, texture: "threads" },
  { ground: "harda", motif: "harda", resist: "harda", outline: null, texture: "threads" },
  { ground: "harda", motif: "harda", resist: "harda", outline: "lime", texture: null },
  { ground: "harda-dry", motif: "harda-dry", resist: "harda-dry", outline: "lime", texture: null },
  { ground: "harda", motif: "harda", resist: "kut", outline: "lime", texture: null },
  { ground: "harda", motif: "kesari", resist: "kut", outline: "lime", texture: null },
  { ground: "harda", motif: "mud", resist: "kut", outline: "lime", texture: "grit" },
  { ground: "indigo", motif: "mud", resist: "kut", outline: "lime", texture: "grit" },
  { ground: "indigo", motif: "mud-wet", resist: "kut", outline: "lime", texture: "grit" },
  { ground: "indigo", motif: "madder", resist: "kut", outline: "pink", texture: null },
  { ground: "indigo-deep", motif: "madder-bright", resist: "kut", outline: "lime", texture: null }
];

export type TextureIds = { weave: string; threads: string; grit: string };

const CORNERS = [[0, 0], [100, 0], [0, 100], [100, 100]] as const;
const EDGES = [[50, 0], [100, 50], [50, 100], [0, 50]] as const;
const QUARTERS = [[25, 25], [75, 25], [25, 75], [75, 75]] as const;
const RING = [[83.26, 63.78], [63.78, 83.26], [36.22, 83.26], [16.74, 63.78], [16.74, 36.22], [36.22, 16.74], [63.78, 16.74], [83.26, 36.22]] as const;

export function dye(name: Dye): string {
  return `var(--dye-${name})`;
}

export function starPath(cx: number, cy: number, r: number): string {
  const a = r * 0.2929;
  const b = r * 0.7071;
  const points = [[0, -r], [a, -b], [b, -b], [b, -a], [r, 0], [b, a], [b, b], [a, b], [0, r], [-a, b], [-b, b], [-b, a], [-r, 0], [-b, -a], [-b, -b], [-a, -b]];
  return `M${points.map(([x, y]) => `${(cx + x).toFixed(2)} ${(cy + y).toFixed(2)}`).join(" L")} Z`;
}

export function diamondPath(cx: number, cy: number, r: number): string {
  return `M${cx} ${cy - r} L${cx + r} ${cy} L${cx} ${cy + r} L${cx - r} ${cy} Z`;
}

function outlined(palette: StagePalette, width: number) {
  return palette.outline ? { stroke: dye(palette.outline), strokeWidth: width } : {};
}

function Motifs({ palette }: { palette: StagePalette }) {
  return (
    <>
      {CORNERS.map(([x, y]) => (
        <g key={`c${x}-${y}`}>
          <circle cx={x} cy={y} r="15" fill={dye(palette.resist)} {...outlined(palette, 2)} />
          <path d={starPath(x, y, 9.05)} fill={dye(palette.motif)} {...outlined(palette, 1.1)} />
          <circle cx={x} cy={y} r="2.2" fill={dye(palette.resist)} />
        </g>
      ))}
      {EDGES.map(([x, y]) => (
        <g key={`e${x}-${y}`}>
          <path d={diamondPath(x, y, 8)} fill={dye(palette.motif)} {...outlined(palette, 1.3)} />
          <circle cx={x} cy={y} r="1.9" fill={dye(palette.resist)} />
        </g>
      ))}
      <path d={starPath(50, 50, 28.99)} fill={dye(palette.motif)} {...outlined(palette, 2.2)} />
      <path d={starPath(50, 50, 16.26)} fill={dye(palette.resist)} {...outlined(palette, 1.2)} />
      <circle cx="50" cy="50" r="4.4" fill={dye(palette.motif)} {...outlined(palette, 1)} />
      {palette.outline ? RING.map(([x, y]) => <circle key={`r${x}-${y}`} cx={x} cy={y} r="2.1" fill={dye(palette.outline as Dye)} />) : null}
      {QUARTERS.map(([x, y]) => (
        <circle key={`q${x}-${y}`} cx={x} cy={y} r="1.6" fill={dye(palette.resist)} />
      ))}
    </>
  );
}

function Texture({ palette, textures, width, height }: { palette: StagePalette; textures: TextureIds; width: number; height: number }) {
  return (
    <>
      {palette.texture === "grit" ? <rect width={width} height={height} fill={`url(#${textures.grit})`} opacity={0.5} /> : null}
      {palette.texture === "threads" ? <rect width={width} height={height} fill={`url(#${textures.threads})`} /> : null}
      <rect width={width} height={height} fill={`url(#${textures.weave})`} />
    </>
  );
}

export function StageTile({ id, palette, textures }: { id: string; palette: StagePalette; textures: TextureIds }) {
  return (
    <pattern id={id} width="100" height="100" patternUnits="userSpaceOnUse">
      <rect width="100" height="100" fill={dye(palette.ground)} />
      {palette.outline ? <rect x="1.4" y="1.4" width="97.2" height="97.2" fill="none" {...outlined(palette, 1.1)} /> : null}
      <Motifs palette={palette} />
      <Texture palette={palette} textures={textures} width={100} height={100} />
    </pattern>
  );
}

export function StageBorder({ id, palette, textures }: { id: string; palette: StagePalette; textures: TextureIds }) {
  return (
    <pattern id={id} width="40" height="44" patternUnits="userSpaceOnUse">
      <rect width="40" height="44" fill={dye(palette.ground)} />
      {palette.outline ? <path d="M0 4 H40 M0 40 H40" stroke={dye(palette.outline)} strokeWidth="1.4" /> : null}
      {palette.outline ? <path d="M0 8 H40 M0 36 H40" stroke={dye(palette.outline)} strokeWidth="0.7" /> : null}
      <path d="M20 12 L30 22 L20 32 L10 22 Z" fill={dye(palette.motif)} {...outlined(palette, 1.1)} />
      <circle cx="20" cy="22" r="3.4" fill={dye(palette.resist)} />
      <path d="M0 12 L10 22 L0 32 M40 12 L30 22 L40 32" fill="none" stroke={dye(palette.resist)} strokeWidth="2.2" />
      <Texture palette={{ ...palette, texture: null }} textures={textures} width={40} height={44} />
    </pattern>
  );
}

export function TexturePatterns({ textures }: { textures: TextureIds }) {
  return (
    <>
      <pattern id={textures.weave} width="3" height="3" patternUnits="userSpaceOnUse">
        <path d="M0 3 L3 0" stroke={dye("kut")} strokeOpacity="0.07" strokeWidth="0.6" />
        <path d="M0 0 L3 3" stroke={dye("cloth")} strokeOpacity="0.06" strokeWidth="0.5" />
      </pattern>
      <pattern id={textures.threads} width="2.5" height="2.5" patternUnits="userSpaceOnUse">
        <path d="M0 .6 H2.5 M.6 0 V2.5" stroke={dye("mud")} strokeOpacity="0.09" strokeWidth="0.45" />
      </pattern>
      <pattern id={textures.grit} width="9" height="9" patternUnits="userSpaceOnUse">
        <circle cx="2" cy="3" r="0.8" fill={dye("kut")} fillOpacity="0.45" />
        <circle cx="6.5" cy="7" r="0.6" fill={dye("cloth")} fillOpacity="0.5" />
        <circle cx="7" cy="1.6" r="0.5" fill={dye("kut")} fillOpacity="0.35" />
      </pattern>
    </>
  );
}
