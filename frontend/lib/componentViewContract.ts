import type { ReactNode } from "react";

import type { MonographComponent } from "@/lib/monographDocument";

export type ComponentViewProps = {
  component: MonographComponent;
  spec: Record<string, unknown>;
  unitRefs: string[];
  renderUnit: (ref: string) => ReactNode;
};

export type ComponentView = (props: ComponentViewProps) => ReactNode;

export type ComponentViews = Readonly<Partial<Record<string, ComponentView>>>;
