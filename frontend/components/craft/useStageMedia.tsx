"use client";

import { useCallback, useEffect, useMemo, useSyncExternalStore, type ReactNode } from "react";

import { useAuth } from "@/components/AuthProvider";
import { StageMedia } from "@/components/craft/StageMedia";
import { CraftMedia, type CraftMediaDeps } from "@/lib/craftMedia";
import { createMediaJob, fetchMediaJob, fetchMediaOptions, setMediaSharing } from "@/lib/mediaContract";
import { sessionJobMemory } from "@/lib/mediaJobMemory";
import { newIdempotencyKey } from "@/lib/mediaView";
import { canShareMedia } from "@/lib/permissions";

function browserMediaDeps(): CraftMediaDeps {
  return {
    api: { options: fetchMediaOptions, create: createMediaJob, job: fetchMediaJob, share: setMediaSharing },
    memory: sessionJobMemory,
    newKey: () => newIdempotencyKey(() => crypto.randomUUID()),
    now: () => Date.now(),
    schedule: (ms, run) => {
      const timer = setTimeout(run, ms);
      return () => clearTimeout(timer);
    }
  };
}

export function useStageMedia(craftSlug: string): (stage: { id: string; name: string }) => ReactNode {
  const media = useMemo(() => new CraftMedia(browserMediaDeps(), craftSlug), [craftSlug]);
  const state = useSyncExternalStore(media.subscribe, media.getState, media.getState);
  const canShare = canShareMedia(useAuth().user);

  useEffect(() => {
    media.start();
    return () => media.dispose();
  }, [media]);

  return useCallback((stage) => <StageMedia stage={stage} media={media} state={state} canShare={canShare} />, [canShare, media, state]);
}
