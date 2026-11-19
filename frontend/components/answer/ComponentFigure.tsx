import { TextLink } from "@/components/ui/TextLink";
import { componentKicker, OPEN_THE_FIGURE, type ComponentBlock } from "@/lib/explainerComponent";

export function ComponentFigure({ block }: { block: ComponentBlock }) {
  const titleId = `${block.id}-title`;
  return (
    <aside className="kv-figure grid min-w-0 gap-1.5" aria-labelledby={titleId} data-testid="component-figure" data-component-kind={block.componentKind} data-label={block.label}>
      <p className="kicker">{componentKicker(block)}</p>
      <h4 id={titleId} className="break-words font-ui text-h4 text-ink-1">
        {block.title}
      </h4>
      <p className="mt-1">
        <TextLink href={block.href} standalone>
          {OPEN_THE_FIGURE}
          <span className="sr-only">: {block.title}</span>
        </TextLink>
      </p>
    </aside>
  );
}
