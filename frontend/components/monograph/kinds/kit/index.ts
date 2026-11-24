import { eitherView } from "@/components/monograph/eitherView";
import { Diagram } from "@/components/monograph/kinds/science/Diagram";
import { KIT_KIND } from "@/lib/componentSpecsKit";
import type { ComponentView } from "@/lib/componentViewContract";

import { KitDiagramView } from "./KitDiagramView";

export const DIAGRAM_VIEW: ComponentView = eitherView(Diagram, KitDiagramView, KIT_KIND);
