import { craftLinkShape, type CraftLink } from "@/lib/answerShapes";
import { envelope, type BlockEnvelope } from "@/lib/explainerBlockBase";
import { list, matching, object, ShapeError, text, type Shape } from "@/lib/shape";

export const COMPONENT_LABEL = matching(/^[a-z0-9]+(-[a-z0-9]+)*(\/[a-z0-9]+(-[a-z0-9]+)*){2,}$/, "a component label");
export const COMPONENT_KIND = matching(/^[a-z][a-z0-9_]*$/, "a component kind");
export const PAGE_ANCHOR = /^#[A-Za-z][A-Za-z0-9_-]*$/;

export type ComponentSource = { sourceId: string };
export type ComponentBlock = BlockEnvelope<"component"> & {
  label: string;
  componentKind: string;
  title: string;
  craft: CraftLink;
  href: string;
  sources: ComponentSource[];
};

const fields = object<ComponentBlock>({
  ...envelope("component"),
  label: COMPONENT_LABEL,
  componentKind: COMPONENT_KIND,
  title: text,
  craft: craftLinkShape,
  href: text,
  sources: list(object<ComponentSource>({ sourceId: text }), 1)
});

export const componentBlockShape: Shape<ComponentBlock> = {
  expected: "a registered component placed from its craft's page",
  parse(value, path) {
    const block = fields.parse(value, path);
    const anchor = block.href.slice(block.craft.path.length);
    const onItsPage = block.href.startsWith(block.craft.path) && (anchor === "" || PAGE_ANCHOR.test(anchor));
    if (!onItsPage || block.componentKind === "component" || block.title.trim() === "") {
      throw new ShapeError(path, "a component linking its craft's page, at most with an anchor");
    }
    return block;
  }
};

export const OPEN_THE_FIGURE = "Open the figure";

export function componentKicker(block: ComponentBlock): string {
  return `Figure from the ${block.craft.name} monograph`;
}

export function componentSourceIds(block: ComponentBlock): string[] {
  return block.sources.map((source) => source.sourceId);
}
