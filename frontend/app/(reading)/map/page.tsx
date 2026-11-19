import type { Metadata } from "next";
import { Suspense } from "react";

import { CraftsMapScreen } from "@/components/map/CraftsMapScreen";
import { Skeleton } from "@/components/ui/Skeleton";

export const metadata: Metadata = {
  title: "Map",
  description: "Where India's crafts are practised, state by state, with district soil, climate and land cover beside them."
};

export default function MapPage() {
  return (
    <Suspense fallback={<Skeleton shape="chart" label="Drawing the map" />}>
      <CraftsMapScreen />
    </Suspense>
  );
}
