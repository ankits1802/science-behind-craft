"use client";

import { useEffect, useState } from "react";

import { MONOGRAPH_KIT_CSS } from "@/lib/monographDocument";

export const KIT_REST_PRECEDENCE = "kit";

export function KitSheetLink() {
  return <link rel="stylesheet" href={MONOGRAPH_KIT_CSS} precedence={KIT_REST_PRECEDENCE} />;
}

export function KitRestSheet() {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  return hydrated ? <KitSheetLink /> : null;
}
