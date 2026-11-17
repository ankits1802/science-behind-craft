"use client";

import { Suspense, useCallback, useState } from "react";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import { BookOpen } from "lucide-react";

import { CraftHeader } from "@/components/craft/CraftHeader";
import { CraftReference } from "@/components/craft/CraftReference";
import { useRemote, type RemoteFailure } from "@/components/hooks/useRemote";
import { PageHeader } from "@/components/PageHeader";
import { RemoteView } from "@/components/RemotePanels";
import { useVoiceAvailability, useVoiceOffered } from "@/components/voice/useVoiceOffer";
import { ApiError } from "@/lib/api";
import { fetchCraftPage } from "@/lib/craftPageContract";
import type { CraftTab } from "@/lib/craftPageView";
import { recordLoadFailure } from "@/lib/recordView";

function pageFailure(failure: RemoteFailure): string {
  const cause = failure.cause;
  return cause instanceof ApiError ? recordLoadFailure("craft", cause.status, cause.message) : recordLoadFailure("craft", null);
}

export default function CraftPage() {
  return (
    <Suspense fallback={null}>
      <CraftScreen />
    </Suspense>
  );
}

function CraftScreen() {
  const { slug } = useParams<{ slug: string }>();
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const page = useRemote(useCallback(() => fetchCraftPage(slug), [slug]));
  const availability = useVoiceAvailability();
  const voiceOffered = useVoiceOffered(availability);
  const [voiceOpen, setVoiceOpen] = useState(false);

  const setTab = useCallback(
    (next: CraftTab) => {
      const search = new URLSearchParams(params.toString());
      if (next === "overview") search.delete("tab");
      else search.set("tab", next);
      const query = search.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [params, pathname, router]
  );

  if (!page.data) {
    return (
      <>
        <PageHeader title="Craft" icon={<BookOpen className="h-5 w-5" aria-hidden />} />
        <RemoteView remote={page} failed={pageFailure}>
          {() => null}
        </RemoteView>
      </>
    );
  }

  return (
    <>
      <CraftHeader craft={page.data.craft} onVoice={voiceOffered ? () => setVoiceOpen(true) : undefined} />
      <CraftReference
        page={page.data}
        requested={params.get("tab")}
        onTab={setTab}
        voice={voiceOffered ? { open: voiceOpen, onClose: () => setVoiceOpen(false), availability } : null}
      />
    </>
  );
}
