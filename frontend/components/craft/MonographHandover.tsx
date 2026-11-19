"use client";

import { useEffect } from "react";

import { Skeleton } from "@/components/ui/Skeleton";
import { cameByRouter } from "@/lib/craftMonographs";

function documentPath(): string | null {
  const [entry] = performance.getEntriesByType("navigation");
  return entry ? new URL(entry.name).pathname : null;
}

export function MonographHandover() {
  useEffect(() => {
    if (cameByRouter(documentPath(), window.location.pathname)) window.location.reload();
  }, []);
  return <Skeleton shape="masthead" label="Opening the monograph" />;
}
