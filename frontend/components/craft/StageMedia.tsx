"use client";

import { Clapperboard, ImagePlus, RotateCw, type LucideIcon } from "lucide-react";

import { MediaFigure } from "@/components/craft/MediaFigure";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { MediaActionButton } from "@/components/ui/MediaActionButton";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { slotKey, type CraftMedia, type CraftMediaState, type MediaSlot } from "@/lib/craftMedia";
import { MEDIA_KINDS, offeredKinds, type MediaKind, type MediaKindOffer } from "@/lib/mediaContract";
import { MEDIA_KIND_LABEL, MEDIA_STALLED, mayRequest, offerLabel, remainingLabel, slotAnnouncement, slotProgress, type WorkingSlot } from "@/lib/mediaView";

type StageRef = { id: string; name: string };
type SlotProps = { kind: MediaKind; stage: StageRef; media: CraftMedia; canShare: boolean };

const KIND_ICON: Record<MediaKind, LucideIcon> = { IMAGE: ImagePlus, VIDEO: Clapperboard };

export function StageMedia({ stage, media, state, canShare }: { stage: StageRef; media: CraftMedia; state: CraftMediaState; canShare: boolean }) {
  const offers = state.options ? offeredKinds(state.options, stage.id) : [];
  const slots = MEDIA_KINDS.flatMap((kind) => {
    const slot = state.slots[slotKey(stage.id, kind)];
    return slot ? [{ kind, slot }] : [];
  });
  if (offers.length === 0 && slots.length === 0) return null;
  const idle = offers.filter((offer) => mayRequest(state.slots[slotKey(stage.id, offer.kind)]));

  return (
    <section aria-label={`Illustrations of ${stage.name}`} className="mt-4 grid gap-4 border-t border-line-200 pt-4" data-testid="stage-media">
      <p role="status" className="sr-only">
        {slots.map(({ kind, slot }) => slotAnnouncement(kind, slot)).join(" ")}
      </p>
      {slots.map(({ kind, slot }) => (
        <SlotView key={kind} kind={kind} slot={slot} stage={stage} media={media} canShare={canShare} />
      ))}
      {idle.length > 0 ? (
        <ActionGroup align="start">
          {idle.map((offer) => (
            <OfferButton
              key={offer.kind}
              offer={offer}
              stageName={stage.name}
              hasResult={state.slots[slotKey(stage.id, offer.kind)]?.phase === "ready"}
              onPress={() => media.request(stage.id, offer.kind)}
            />
          ))}
        </ActionGroup>
      ) : null}
    </section>
  );
}

function SlotView({ kind, slot, stage, media, canShare }: SlotProps & { slot: MediaSlot }) {
  switch (slot.phase) {
    case "creating":
    case "open":
      return <SlotProgress kind={kind} slot={slot} stageName={stage.name} />;
    case "ready":
      return (
        <MediaFigure
          kind={kind}
          asset={slot.asset}
          canShare={canShare}
          actions={{
            refresh: () => media.refresh(stage.id, kind),
            fresh: () => media.freshAsset(stage.id, kind),
            share: (action) => media.share(stage.id, kind, action)
          }}
        />
      );
    case "lost":
      return <SlotNotice kind={kind} message={slot.message} retry={{ label: "Try again", run: () => media.retry(stage.id, kind) }} />;
    case "stalled":
      return <SlotNotice kind={kind} message={MEDIA_STALLED} retry={{ label: "Check again", run: () => media.retry(stage.id, kind) }} />;
    default:
      return <SlotNotice kind={kind} message={slot.message} />;
  }
}

function SlotProgress({ kind, slot, stageName }: { kind: MediaKind; slot: WorkingSlot; stageName: string }) {
  const progress = slotProgress(kind, slot);
  return (
    <div className="grid max-w-md gap-1.5">
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="font-medium text-ink-900">{MEDIA_KIND_LABEL[kind]}</span>
        <span className="text-ink-500">{progress.word}</span>
      </div>
      <ProgressBar
        percent={progress.percent}
        role="progressbar"
        aria-label={`${MEDIA_KIND_LABEL[kind]}, ${stageName}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progress.percent}
        aria-valuetext={progress.word}
        fillClassName="transition-[width] duration-500 ease-out"
      />
    </div>
  );
}

function SlotNotice({ kind, message, retry }: { kind: MediaKind; message: string; retry?: { label: string; run: () => void } }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
      <p className="min-w-0 text-sm text-ink-700">
        <span className="font-medium text-ink-900">{MEDIA_KIND_LABEL[kind]} · </span>
        {message}
      </p>
      {retry ? (
        <ActionGroup className="max-sm:w-full">
          <MediaActionButton label={retry.label} icon={<RotateCw className="h-4 w-4" aria-hidden />} onClick={retry.run} />
        </ActionGroup>
      ) : null}
    </div>
  );
}

function OfferButton({ offer, stageName, hasResult, onPress }: { offer: MediaKindOffer; stageName: string; hasResult: boolean; onPress: () => void }) {
  const Icon = KIND_ICON[offer.kind];
  const remaining = remainingLabel(offer);
  return (
    <button type="button" className="field-button-secondary" onClick={onPress} data-testid={`stage-media-${offer.kind.toLowerCase()}`}>
      <Icon className="h-4 w-4" aria-hidden />
      <span>{offerLabel(offer.kind, hasResult)}</span>
      {remaining ? (
        <span className="text-xs font-normal text-ink-500">
          <span className="sr-only">, </span>
          {remaining}
        </span>
      ) : null}
      <span className="sr-only">, {stageName}</span>
    </button>
  );
}
