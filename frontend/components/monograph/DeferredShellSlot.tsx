"use client";

import { startTransition, useCallback, useEffect, useRef, useState, type ComponentType } from "react";

import { KitSheetLink } from "@/components/monograph/KitRestSheet";
import { announce, SHELL_COMPLETE_EVENT } from "@/components/monograph/kitGate";
import { hashTargetMissing, useShellTrigger } from "@/components/monograph/useShellTrigger";
import type { DocumentRest, RestPart, ShellRest } from "@/lib/monographRenderShell";
import { fetchedDocumentRest, fetchedShellRest, REST_UNREAD, type RestFetcher } from "@/lib/monographRestRead";

type RestView<T> = ComponentType<{ part: T; jump: string | null }>;
type ReadRest = { part: "document"; View: RestView<DocumentRest>; rest: DocumentRest } | { part: "shell"; View: RestView<ShellRest>; rest: ShellRest };
type Shown = ReadRest & { jump: string | null };

const fetchRest: RestFetcher = (src) => fetch(src);

async function readRest(src: string, version: number, part: RestPart): Promise<ReadRest> {
  if (part === "document") {
    const [loaded, rest] = await Promise.all([import("@/components/monograph/DeferredDocument"), fetchedDocumentRest(fetchRest, src, version)]);
    return { part, View: loaded.DeferredDocument, rest };
  }
  const [loaded, rest] = await Promise.all([import("@/components/monograph/DeferredShell"), fetchedShellRest(fetchRest, src, version)]);
  return { part, View: loaded.DeferredShell, rest };
}

function missingTarget(): string | null {
  return hashTargetMissing(window.location.hash, document) ? decodeURIComponent(window.location.hash.slice(1)) : null;
}

function ShownRest({ shown }: { shown: Shown }) {
  return (
    <>
      <KitSheetLink />
      {shown.part === "document" ? <shown.View part={shown.rest} jump={shown.jump} /> : <shown.View part={shown.rest} jump={shown.jump} />}
    </>
  );
}

function Unread() {
  useEffect(() => announce(window, SHELL_COMPLETE_EVENT), []);
  return (
    <p role="status" className="kv-wrap font-ui text-ui text-ink-2">
      {REST_UNREAD}
    </p>
  );
}

export function DeferredShellSlot({ src, version, part = "shell" }: { src: string; version: number; part?: RestPart }) {
  const holder = useRef<HTMLDivElement | null>(null);
  const [shown, setShown] = useState<Shown | null>(null);
  const [failed, setFailed] = useState(false);
  const start = useCallback(() => {
    readRest(src, version, part).then(
      (read) => startTransition(() => setShown({ ...read, jump: missingTarget() })),
      () => setFailed(true)
    );
  }, [src, version, part]);
  useShellTrigger(holder, start);
  if (shown) return <ShownRest shown={shown} />;
  if (failed) return <Unread />;
  return <div ref={holder} className="min-h-[300vh]" aria-busy="true" data-kv-deferred="" />;
}
