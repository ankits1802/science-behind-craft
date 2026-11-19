"use client";

import { useCallback, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { BookOpen } from "lucide-react";

import { CraftHeader } from "@/components/craft/CraftHeader";
import { CraftReference } from "@/components/craft/CraftReference";
import { useHasSession } from "@/components/hooks/useHasSession";
import { useRemote, type RemoteFailure } from "@/components/hooks/useRemote";
import { PageHeader } from "@/components/PageHeader";
import { RemoteView } from "@/components/RemotePanels";
import { useVoiceAvailability, useVoiceOffered } from "@/components/voice/useVoiceOffer";
import { ApiError } from "@/lib/api";
import { fetchCraftPage, type CraftPage } from "@/lib/craftPageContract";
import type { CraftTab } from "@/lib/craftPageView";
import { recordLoadFailure } from "@/lib/recordView";

function pageFailure(failure: RemoteFailure): string {
  const cause = failure.cause;
  return cause instanceof ApiError ? recordLoadFailure("craft", cause.status, cause.message) : recordLoadFailure("craft", null);
}

export function CraftScreen({ slug, initial, version }: { slug: string; initial: CraftPage | null; version?: number }) {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const signedIn = useHasSession();
  const load = useCallback(() => fetchCraftPage(slug, version), [slug, version]);
  const remote = useRemote(initial && !signedIn ? null : load);
  const page = remote.data ?? initial;
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

  if (!page) {
    return (
      <>
        <PageHeader title="Craft" icon={<BookOpen className="h-5 w-5" aria-hidden />} />
        <RemoteView remote={remote} failed={pageFailure}>
          {() => null}
        </RemoteView>
      </>
    );
  }

  return (
    <>
      <CraftHeader craft={page.craft} onVoice={voiceOffered ? () => setVoiceOpen(true) : undefined} />
      <CraftReference
        page={page}
        requested={params.get("tab")}
        onTab={setTab}
        voice={voiceOffered ? { open: voiceOpen, onClose: () => setVoiceOpen(false), availability } : null}
      />
    </>
  );
}
