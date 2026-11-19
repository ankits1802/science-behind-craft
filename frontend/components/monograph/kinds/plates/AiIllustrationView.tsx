import { aiIllustrationShape, type ArtFrame } from "@/lib/componentSpecsPlates";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

import { AiTag, DownloadIcon } from "./KitIcons";
import { illustrationCaption, illustrationMeta } from "./mediaCopy";

export function ArtSymbol({ art, className }: { art: ArtFrame; className: string }) {
  return (
    <svg viewBox={art.viewBox} preserveAspectRatio="xMidYMid slice" aria-hidden="true" className={className}>
      <use href={`#${art.symbol}`} width={art.width} height={art.height} />
    </svg>
  );
}

export function AiIllustrationView({ spec }: ComponentViewProps) {
  const illustration = parseShape(aiIllustrationShape, spec);
  const art = illustration.art;
  return (
    <figure className="ai ai-only" data-sec={illustration.section} data-sym={art.symbol}>
      <div className="ai-art" role="img" aria-label={`AI illustration: ${illustration.subject}`}>
        <ArtSymbol art={art} className="ai-soft" />
        <ArtSymbol art={art} className="ai-pic" />
        <span className="ai-edge" aria-hidden="true"></span>
        <span className="ai-job" aria-hidden="true">
          <span className="ai-job-t">Drawing</span>
          <span className="meter">
            <b style={{ width: "0%" }}></b>
          </span>
        </span>
      </div>
      <AiTag label="AI illustration" />
      <figcaption className="ai-cap">
        <span>{illustrationCaption(illustration.subject, illustration.sentences)}</span>
        <span className="meta">{illustrationMeta(illustration.made)}</span>
        <button className="dl" type="button" data-dl-ill={art.symbol} data-name={illustration.downloadName}>
          <DownloadIcon />
          Download
        </button>
      </figcaption>
    </figure>
  );
}
