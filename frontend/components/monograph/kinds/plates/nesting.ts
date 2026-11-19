import type { ReactNode } from "react";

import type { ComponentViewProps } from "@/lib/componentViewContract";

export type NestingViewProps = ComponentViewProps;

export function heldComponent(props: ComponentViewProps, label: string | null): ReactNode {
  return label ? props.renderComponent(label) : null;
}
