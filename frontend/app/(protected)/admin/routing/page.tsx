"use client";

import { Route } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { RoutingPanel } from "@/components/settings/RoutingPanel";

export default function RoutingPage() {
  return (
    <>
      <PageHeader title="AI routing" description="The first working model in each list takes the call." icon={<Route className="h-5 w-5" aria-hidden />} />
      <RoutingPanel />
    </>
  );
}
