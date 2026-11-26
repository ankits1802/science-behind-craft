import { drawingSource, drawingViewBox, THEME_VARIANTS } from "@/lib/componentSpecsGeneral";
import { drawsOnBase, wordedStill, type CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";

import { CodedStillBaseView } from "./CodedStillBase";

type StillProps = { figure: Pick<CodedFigureSpec, "still" | "themes" | "base">; words: Readonly<Record<string, string>> };

export function CodedStill({ figure, words }: StillProps) {
  const box = figure.still ? drawingViewBox(figure.still) : null;
  if (!figure.themes || !box) return <div className="w-full bg-sunk" style={{ aspectRatio: "16 / 9" }} aria-hidden="true" data-coded-still="none" />;
  const themes = figure.themes;
  const base = figure.base && drawsOnBase(figure.still) ? figure.base : null;
  return (
    <div className="relative w-full [forced-color-adjust:none]" aria-hidden="true" data-coded-still="">
      {base ? <CodedStillBaseView base={base.still} dams={base.dams} /> : null}
      {THEME_VARIANTS.map((variant) => (
        // eslint-disable-next-line @next/next/no-img-element -- a coded figure's still is an SVG drawn as an image so it runs no script, which next/image would not load from a data URI
        <img key={variant} src={drawingSource(wordedStill(themes[variant], words))} width={box.width} height={box.height} alt="" className="kv-themed relative h-auto w-full" data-theme-variant={variant} />
      ))}
    </div>
  );
}
