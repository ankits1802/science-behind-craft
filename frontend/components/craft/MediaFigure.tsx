"use client";

import { useId, useState } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { Download, RotateCw, Sparkles } from "lucide-react";

import { MediaShareButton } from "@/components/craft/MediaShareButton";
import { riseItem } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { MediaActionButton } from "@/components/ui/MediaActionButton";
import { downloadFile } from "@/lib/download";
import type { MediaAsset, MediaKind, MediaShareAction } from "@/lib/mediaContract";
import { assetCredit, isUnexpected, MEDIA_BROKEN, MEDIA_DOWNLOAD_FAILED, MEDIA_KIND_LABEL, shareStatus, shareStep, urlIsFresh } from "@/lib/mediaView";
import { cn } from "@/lib/utils";

export type FigureActions = {
  refresh: () => Promise<MediaAsset>;
  fresh: () => Promise<MediaAsset>;
  share: (action: MediaShareAction) => Promise<void>;
};

export function MediaFigure({ kind, asset, actions, canShare }: { kind: MediaKind; asset: MediaAsset; actions: FigureActions; canShare: boolean }) {
  const reduce = useAppReducedMotion();
  const altId = useId();
  const [brokenUrl, setBrokenUrl] = useState<string | null>(null);
  const [renewed, setRenewed] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const noun = MEDIA_KIND_LABEL[kind].toLowerCase();
  const status = canShare ? shareStatus(asset) : null;
  const step = canShare ? shareStep(asset) : null;

  const renew = (quiet: boolean) => {
    setRenewed(true);
    setBrokenUrl(null);
    actions.refresh().catch((error: unknown) => {
      if (isUnexpected(error)) console.error(error);
      if (!quiet) setProblem(MEDIA_BROKEN);
      setBrokenUrl(asset.url);
    });
  };

  const onBroken = () => {
    if (!renewed && !urlIsFresh(asset, Date.now())) renew(true);
    else setBrokenUrl(asset.url);
  };

  const download = async () => {
    setDownloading(true);
    setProblem(null);
    try {
      const fresh = await actions.fresh();
      await downloadFile(fresh.url, fresh.fileName);
    } catch (error) {
      if (isUnexpected(error)) console.error(error);
      setProblem(MEDIA_DOWNLOAD_FAILED);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <motion.figure variants={riseItem(reduce)} initial="hidden" animate="show" className="grid gap-2" data-testid="stage-media-figure">
      <div className={cn("overflow-hidden rounded-md border border-line-200 bg-surface-50", kind === "IMAGE" ? "max-w-md" : "max-w-xl")}>
        {brokenUrl === asset.url ? (
          <div className="grid aspect-video place-items-center gap-2 p-4 text-center">
            <p className="text-sm text-ink-700">{MEDIA_BROKEN}</p>
            <MediaActionButton label="Try again" icon={<RotateCw className="h-4 w-4" aria-hidden />} onClick={() => renew(false)} />
          </div>
        ) : kind === "IMAGE" ? (
          <Image key={asset.url} unoptimized src={asset.url} alt={asset.altText} width={asset.width} height={asset.height} onError={onBroken} className="h-auto w-full" />
        ) : (
          <video
            key={asset.url}
            src={asset.url}
            width={asset.width}
            height={asset.height}
            controls
            muted
            playsInline
            preload="metadata"
            aria-describedby={altId}
            onError={onBroken}
            className="h-auto w-full"
          />
        )}
      </div>
      {kind === "VIDEO" ? (
        <p id={altId} className="sr-only">
          {asset.altText}
        </p>
      ) : null}
      <figcaption className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-500">
          <span className="inline-flex items-center gap-1 rounded-full border border-line-200 bg-surface-50 px-2 py-0.5 text-[11px] font-semibold text-ink-700">
            <Sparkles className="h-3 w-3" aria-hidden />
            {asset.label.text}
          </span>{" "}
          <span>{assetCredit(asset)}</span>{" "}
          {status ? <span className="font-medium text-ink-700">· {status}</span> : null}
        </span>
        <ActionGroup align="end" className="max-sm:w-full">
          <MediaActionButton
            label={downloading ? "Downloading…" : "Download"}
            icon={<Download className="h-4 w-4" aria-hidden />}
            onClick={() => void download()}
            disabled={downloading}
            accessibleLabel={downloading ? undefined : `Download this ${noun}`}
          />
          {step ? <MediaShareButton step={step} noun={noun} onShare={actions.share} onProblem={setProblem} /> : null}
        </ActionGroup>
      </figcaption>
      {problem ? (
        <p role="alert" className="text-sm text-error-600 dark:text-red-400">
          {problem}
        </p>
      ) : null}
    </motion.figure>
  );
}
