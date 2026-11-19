import type { ComponentViewProps } from "@/lib/componentViewContract";
import { diagramShape, type Chain, type ChainPart } from "@/lib/componentSpecsScienceFigures";
import { parseShape } from "@/lib/shape";

import { GroupedLine, TickedCount } from "./parts/Chemistry";
import { Drawing } from "./parts/Drawing";
import { Block, type RenderUnit } from "./parts/Text";

function ChainPartView({ part, renderUnit }: { part: ChainPart; renderUnit: RenderUnit }) {
  if (part.part === "text") return <Block block={part.text} renderUnit={renderUnit} />;
  if (part.part === "drawing") return <Drawing node={part.drawing} />;
  if (part.part === "step") {
    return (
      <p className="ch-t">
        <a className="inline" href={`#${part.player}`} data-rp-step={`${part.player}:${part.step}`}>
          <span className="kv-figref" data-figref={part.figure}>
            {part.figureLabel}
          </span>
          {`, step ${part.step}`}
        </a>
      </p>
    );
  }
  return (
    <div className={`ch-eq ${part.style}`}>
      <p className="kv-eq-k">{renderUnit(part.label)}</p>
      <GroupedLine line={part} label={part.lineLabel} />
      <TickedCount count={part.count} />
    </div>
  );
}

function ChainView({ chain, renderUnit }: { chain: Chain; renderUnit: RenderUnit }) {
  return (
    <section className="chain" aria-labelledby={chain.headingId}>
      <h2 className="chain-h" id={chain.headingId}>
        {renderUnit(chain.heading)}
      </h2>
      <ol className="ch-ol">
        {chain.links.map((link) => (
          <li key={link.kicker} className={link.style ? `ch ${link.style}` : "ch"}>
            <p className="ch-k">{renderUnit(link.kicker)}</p>
            {link.parts.map((part, index) => <ChainPartView key={index} part={part} renderUnit={renderUnit} />)}
          </li>
        ))}
      </ol>
    </section>
  );
}

export function Diagram({ spec, renderUnit }: ComponentViewProps) {
  const diagram = parseShape(diagramShape, spec);
  return diagram.chain ? <ChainView chain={diagram.chain} renderUnit={renderUnit} /> : <Drawing node={diagram.drawing!} />;
}
