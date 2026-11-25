import type { CSSProperties, ReactNode } from "react";

import type { FrameCrop, SlotPlacement } from "@/lib/monographPlacement";
import type { ComponentHome as Home, FrameStep } from "@/lib/monographScopes";

const PASS_THROUGH: CSSProperties = { display: "contents" };
export const HOME_SPACING = "my-12";
export const BESIDE_SIZE = "MARGIN";

export type FragmentHost = { id: string; html: string };

type HomeProps = { home: Home; label: string; kind: string; fragment?: FragmentHost; placing?: SlotPlacement; children?: ReactNode };

type StepProps = { className?: string; style?: CSSProperties; lang?: string; dir?: string; "data-ui-lang"?: string };

function stepProps(step: FrameStep): StepProps {
  const marks: Readonly<Record<string, string | undefined>> = step.attrs ?? {};
  return { className: step.classes.length ? step.classes.join(" ") : undefined, style: step.box ? undefined : PASS_THROUGH, lang: marks.lang, dir: marks.dir, "data-ui-lang": marks["data-ui-lang"] };
}

function nested(steps: readonly FrameStep[], inner: ReactNode): ReactNode {
  return steps.reduceRight<ReactNode>((child, step) => <div {...stepProps(step)}>{child}</div>, inner);
}

function hosted(steps: readonly FrameStep[], fragment: FragmentHost): ReactNode {
  const last = steps[steps.length - 1];
  const host = last ? stepProps(last) : { style: PASS_THROUGH };
  const inner = <div {...host} id={fragment.id} dangerouslySetInnerHTML={{ __html: fragment.html }} />;
  return nested(steps.slice(0, -1), inner);
}

export function cropStyle(crop: FrameCrop): CSSProperties {
  return {
    "--kv-crop-x": String(crop.x),
    "--kv-crop-y": String(crop.y),
    "--kv-crop-w": String(crop.width),
    "--kv-crop-h": String(crop.height),
    "--kv-crop-ratio": String(Math.round(crop.ratio * 10000) / 10000)
  } as CSSProperties;
}

function homeClass(home: Home, placing: SlotPlacement | undefined): string {
  const spacing = placing?.size === BESIDE_SIZE ? null : HOME_SPACING;
  return [home.scope ? `bx bx-${home.scope}` : null, spacing].filter(Boolean).join(" ");
}

export function ComponentHome({ home, label, kind, fragment, placing, children }: HomeProps) {
  const crop = placing?.crop ?? null;
  return (
    <div
      className={homeClass(home, placing)}
      data-component={label}
      data-component-kind={kind}
      data-home={home.source}
      data-size={placing?.size?.toLowerCase()}
      data-crop={crop ? "" : undefined}
      style={crop ? cropStyle(crop) : undefined}
    >
      {fragment ? hosted(home.frame, fragment) : nested(home.frame, children)}
    </div>
  );
}
