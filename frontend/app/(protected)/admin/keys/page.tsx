"use client";

import { KeyRound } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { ApiKeysPanel } from "@/components/settings/ApiKeysPanel";

export default function ApiKeysPage() {
  return (
    <>
      <PageHeader title="API keys" description="Provider keys. Changes apply everywhere at once." icon={<KeyRound className="h-5 w-5" aria-hidden />} />
      <ApiKeysPanel />
    </>
  );
}
