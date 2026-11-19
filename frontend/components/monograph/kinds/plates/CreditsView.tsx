import { Fragment } from "react";

import { creditsShape } from "@/lib/componentSpecsPlates";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

import { HeldText } from "./HeldText";

export function CreditsView({ spec, renderUnit }: ComponentViewProps) {
  const credits = parseShape(creditsShape, spec);
  return (
    <section className="wrap credits kv-credits">
      {credits.groups.map((group) => (
        <Fragment key={group.title}>
          <h3 className="cr-sub">{renderUnit(group.title)}</h3>
          <ul className={group.listClass ?? undefined}>
            {group.lines.map((line, index) => (
              <li key={line.unit ?? `held-${index}`}>{line.unit ? renderUnit(line.unit) : <HeldText nodes={line.text ?? []} />}</li>
            ))}
          </ul>
        </Fragment>
      ))}
    </section>
  );
}
