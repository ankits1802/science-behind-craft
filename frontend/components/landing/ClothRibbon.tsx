"use client";

import { useId } from "react";

import { STAGE_PALETTES, StageBorder, StageTile, TexturePatterns, dye, type TextureIds } from "@/components/landing/clothTile";
import type { LandingStage } from "@/components/landing/landingContent";
import { TextLink } from "@/components/ui/TextLink";

const BORDER = 44;
const EDGE_STEP = 26;

type Drawing = { width: number; height: number; className: string; key: string };

const DRAWINGS: readonly Drawing[] = [
  { width: 1600, height: 520, className: "kv-ribbon-desk", key: "desk" },
  { width: 660, height: 600, className: "kv-ribbon-phone", key: "phone" }
];

export function edgeX(edge: number, row: number, bandWidth: number, count: number): number {
  if (edge === 0 || edge === count) return edge * bandWidth;
  return edge * bandWidth + (((edge * 7 + row * 13) % 5) - 2) * 1.6;
}

export function bandPath(band: number, drawing: { width: number; height: number }, count: number): string {
  const bandWidth = drawing.width / count;
  const rows = Math.ceil(drawing.height / EDGE_STEP);
  const left = Array.from({ length: rows + 1 }, (_, row) => `${edgeX(band, row, bandWidth, count).toFixed(1)} ${Math.min(row * EDGE_STEP, drawing.height)}`);
  const right = Array.from({ length: rows + 1 }, (_, row) => `${edgeX(band + 1, rows - row, bandWidth, count).toFixed(1)} ${Math.min((rows - row) * EDGE_STEP, drawing.height)}`);
  return `M${[...left, ...right].join(" L")} Z`;
}

function RibbonDrawing({ drawing, prefix, count }: { drawing: Drawing; prefix: string; count: number }) {
  const bandWidth = drawing.width / count;
  return (
    <svg className={drawing.className} viewBox={`0 0 ${drawing.width} ${drawing.height}`} preserveAspectRatio="xMidYMid slice" aria-hidden focusable="false">
      <defs>
        {Array.from({ length: count }, (_, band) => (
          <clipPath key={band} id={`${prefix}-${drawing.key}-clip-${band}`}>
            <path d={bandPath(band, drawing, count)} />
          </clipPath>
        ))}
      </defs>
      {Array.from({ length: count }, (_, band) => (
        <g key={band} clipPath={`url(#${prefix}-${drawing.key}-clip-${band})`}>
          <rect x={band * bandWidth - 6} y="0" width={bandWidth + 12} height={drawing.height} fill={`url(#${prefix}-tile-${band})`} />
          <rect x={band * bandWidth - 6} y="0" width={bandWidth + 12} height={BORDER} fill={`url(#${prefix}-border-${band})`} />
          <rect x={band * bandWidth - 6} y={drawing.height - BORDER} width={bandWidth + 12} height={BORDER} fill={`url(#${prefix}-border-${band})`} />
        </g>
      ))}
      <path d={`M0 ${BORDER} H${drawing.width} M0 ${drawing.height - BORDER} H${drawing.width}`} stroke={dye("kut")} strokeOpacity="0.18" strokeWidth="1" />
    </svg>
  );
}

function RibbonPatterns({ prefix }: { prefix: string }) {
  const textures: TextureIds = { weave: `${prefix}-weave`, threads: `${prefix}-threads`, grit: `${prefix}-grit` };
  return (
    <svg width="0" height="0" className="absolute" aria-hidden focusable="false">
      <defs>
        <TexturePatterns textures={textures} />
        {STAGE_PALETTES.map((palette, band) => (
          <g key={band}>
            <StageTile id={`${prefix}-tile-${band}`} palette={palette} textures={textures} />
            <StageBorder id={`${prefix}-border-${band}`} palette={palette} textures={textures} />
          </g>
        ))}
      </defs>
    </svg>
  );
}

export function ClothRibbon({ stages, name, craftPath }: { stages: readonly LandingStage[]; name: string; craftPath: string | null }) {
  const prefix = `kv-cloth${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  if (stages.length !== STAGE_PALETTES.length) return null;
  return (
    <section className="kv-ribbon" aria-labelledby={`${prefix}-h`}>
      <div className="kv-shell-wrap kv-ribbon-head">
        <p className="kicker" id={`${prefix}-h`}>{`One ${name}, drawn after each of its ${stages.length} stages`}</p>
        {craftPath ? (
          <TextLink href={`${craftPath}#made`} standalone>
            How it is made
          </TextLink>
        ) : null}
      </div>
      <ol className="kv-ruler" aria-hidden>
        {stages.map((stage) => (
          <li key={stage.order}>
            <b>{stage.order}</b>
            {stage.local ? <i>{stage.label}</i> : <span>{stage.label}</span>}
          </li>
        ))}
      </ol>
      <div className="kv-ribbon-cloth" role="img" aria-label={`A ${name} drawn after each of its ${stages.length} stages, from scoured white cotton at the left to the finished indigo and madder cloth at the right`}>
        <RibbonPatterns prefix={prefix} />
        {DRAWINGS.map((drawing) => (
          <RibbonDrawing key={drawing.key} drawing={drawing} prefix={prefix} count={stages.length} />
        ))}
      </div>
      <p className="kv-shell-wrap kv-src-line">Stages and their names from the {name} monograph. The motif is drawn, not traced.</p>
    </section>
  );
}
