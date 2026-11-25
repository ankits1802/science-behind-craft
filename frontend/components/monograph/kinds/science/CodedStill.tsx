import { drawingSource, drawingViewBox, THEME_VARIANTS } from "@/lib/componentSpecsGeneral";
import { wordedStill, type CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";

type StillProps = { figure: Pick<CodedFigureSpec, "still" | "themes">; words: Readonly<Record<string, string>> };

export function CodedStill({ figure, words }: StillProps) {
  const box = figure.still ? drawingViewBox(figure.still) : null;
  if (!figure.themes || !box) return <div className="w-full bg-sunk" style={{ aspectRatio: "16 / 9" }} aria-hidden="true" data-coded-still="none" />;
  const themes = figure.themes;
  return (
    <div className="w-full [forced-color-adjust:none]" aria-hidden="true" data-coded-still="">
      {THEME_VARIANTS.map((variant) => (
        // eslint-disable-next-line @next/next/no-img-element -- a coded figure's still is an SVG drawn as an image so it runs no script, which next/image would not load from a data URI
        <img key={variant} src={drawingSource(wordedStill(themes[variant], words))} width={box.width} height={box.height} alt="" className="kv-themed h-auto w-full" data-theme-variant={variant} />
      ))}
    </div>
  );
}
