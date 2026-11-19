import { createElement, type ReactNode } from "react";

import { HeldText } from "@/components/monograph/kinds/plates/HeldText";
import type { FigureHead, Placed, TextLine } from "@/lib/componentSpecsData";

type RenderUnit = (ref: string) => ReactNode;

export function TextLineView({ line, renderUnit }: { line: TextLine; renderUnit: RenderUnit }) {
  const content = line.unit ? renderUnit(line.unit) : line.text ? <HeldText nodes={line.text} /> : null;
  return createElement(line.tag, { className: line.classes.length ? line.classes.join(" ") : undefined }, content);
}

export function TextLines({ lines, renderUnit }: { lines: TextLine[]; renderUnit: RenderUnit }) {
  return (
    <>
      {lines.map((line, index) => (
        <TextLineView key={line.unit ?? `held-${index}`} line={line} renderUnit={renderUnit} />
      ))}
    </>
  );
}

export function labelledBy(head: FigureHead): string | undefined {
  const ids = [head.titleId, head.dekId].filter((id): id is string => Boolean(id));
  return ids.length ? ids.join(" ") : undefined;
}

export function FigureHeadView({ head, renderUnit }: { head: FigureHead; renderUnit: RenderUnit }) {
  return (
    <>
      {head.number ? (
        <p className="fig-no" data-fig={head.number.ref}>
          {renderUnit(head.number.unit)}
        </p>
      ) : null}
      <p className="chart-title" id={head.titleId ?? undefined}>
        {renderUnit(head.title)}
      </p>
      {head.dek ? (
        <p className="chart-dek" id={head.dekId ?? undefined}>
          {renderUnit(head.dek)}
        </p>
      ) : null}
    </>
  );
}

export function PlacedLabel({ label }: { label: Placed }) {
  const style = Object.fromEntries(
    (["left", "width", "top"] as const).flatMap((side) => (label[side] ? [[side, label[side]]] : []))
  );
  return (
    <span className={label.classes.join(" ")} style={style} aria-hidden={label.hidden ? "true" : undefined}>
      {label.text ? <HeldText nodes={label.text} /> : null}
    </span>
  );
}
