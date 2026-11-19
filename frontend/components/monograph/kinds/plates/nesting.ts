import type { ReactNode } from "react";

import type { ComponentViewProps } from "@/lib/componentViewContract";

export type NestingViewProps = ComponentViewProps & { renderComponent?: (label: string) => ReactNode };

export function heldComponent(props: NestingViewProps, label: string | null): ReactNode {
  return label && props.renderComponent ? props.renderComponent(label) : null;
}
