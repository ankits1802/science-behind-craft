import { createElement, type ReactNode } from "react";

import type { FigureHead, TextBlock } from "@/lib/componentSpecsScienceParts";

export type RenderUnit = (ref: string) => ReactNode;

export function Block({ block, renderUnit }: { block: TextBlock; renderUnit: RenderUnit }) {
  return createElement(block.tag, { className: block.style ?? undefined }, renderUnit(block.unit));
}

export function Blocks({ blocks, renderUnit }: { blocks: TextBlock[]; renderUnit: RenderUnit }) {
  return blocks.map((block) => <Block key={block.unit} block={block} renderUnit={renderUnit} />);
}

export function FigureHeadLines({ head, renderUnit, dekStyle = null }: { head: FigureHead; renderUnit: RenderUnit; dekStyle?: string | null }) {
  return (
    <>
      <p className="fig-no" data-fig={head.figure ?? undefined}>
        {renderUnit(head.number)}
      </p>
      <p className="chart-title" id={head.titleId ?? undefined}>
        {renderUnit(head.title)}
      </p>
      {head.dek ? <p className={dekStyle ? `chart-dek ${dekStyle}` : "chart-dek"}>{renderUnit(head.dek)}</p> : null}
    </>
  );
}
