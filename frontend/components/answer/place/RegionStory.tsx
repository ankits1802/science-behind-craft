"use client";

import { useCallback, useMemo, useRef, type RefObject } from "react";

import { AnswerFigure } from "@/components/answer/place/AnswerFigure";
import { AnswerMapSource } from "@/components/answer/place/AnswerMapSource";
import { MapPlaceholder } from "@/components/answer/place/MapPlaceholder";
import { RiverStage, type StageFocus } from "@/components/answer/place/RiverStage";
import { StoryKey, StoryLayerPicker } from "@/components/answer/place/StoryKey";
import { shownLayerFill, storyLayerInView } from "@/components/answer/place/storyLayer";
import { StoryLayerReadout } from "@/components/answer/place/StoryLayerReadout";
import { storyGeometry, storyTone, type StoryGeometry } from "@/components/answer/place/storyGeometry";
import { StorySteps } from "@/components/answer/place/StorySteps";
import { useRiverFlow, type RiverFlow } from "@/components/answer/place/useRiverFlow";
import { useStoryLayer, type StoryLayer } from "@/components/answer/place/useStoryLayer";
import { DatasetCredit } from "@/components/DatasetCredit";
import { useRemote, type Remote } from "@/components/hooks/useRemote";
import type { DistrictFill } from "@/components/map/DistrictLayer";
import { IndiaLocator, LOCATOR_INSET, locatorLabel } from "@/components/map/IndiaLocator";
import { MapRetry } from "@/components/map/MapRetry";
import { loadShapes, type DistrictShape } from "@/components/map/shapeGeometry";
import { usePlayInView, type PlayInView } from "@/components/motion/usePlayInView";
import { PlayPauseButton } from "@/components/ui/PlayPauseButton";
import { HYDRORIVERS_DATASET_CODE, type RegionStoryBlock, type RiverPath } from "@/lib/explainerPlace";
import { boundaryNote, datasetRow, isGone } from "@/lib/placeView";
import type { MapLayer } from "@/lib/regionContract";
import { ALL_PASSED, missingReaches, stopBeat, storyStatus, storyStops, storySummary, storyTitle } from "@/lib/regionStory";
import { fetchRiverBasin, type RiverBasin } from "@/lib/riverTopology";
import { ShapeError } from "@/lib/shape";

const NO_THRESHOLDS: readonly number[] = [];
const NO_ENTRIES: ReadonlyMap<number, number> = new Map();

type StoryPlay = { play: PlayInView; drawn: boolean; flow: RiverFlow };

function useStoryBasin(river: RiverPath | null): Remote<RiverBasin> {
  const mainRiv = river?.mainRiv ?? null;
  const reachIds = river?.reachIds;
  const load = useCallback(async () => {
    const basin = await fetchRiverBasin(mainRiv as number);
    const missing = missingReaches(reachIds ?? [], basin.reaches);
    if (missing.length > 0) throw new ShapeError(`river ${mainRiv}`, `reaches ${missing.join(", ")} in its basin`);
    return basin;
  }, [mainRiv, reachIds]);
  return useRemote(mainRiv === null ? null : load);
}

function useStoryFill(geometry: StoryGeometry | null, story: StoryLayer, passed: number): { fillOf: DistrictFill; shown: MapLayer | null } {
  const data = story.layer.data;
  const shown = useMemo(() => (data && geometry ? storyLayerInView(geometry, data) : null), [data, geometry]);
  const layered = useMemo(() => (shown ? shownLayerFill(shown) : null), [shown]);
  const fillOf = useCallback(
    (shape: DistrictShape) => {
      if (layered) return layered(shape);
      return geometry ? storyTone(geometry, shape.lgd, passed) : null;
    },
    [layered, geometry, passed]
  );
  return { fillOf, shown };
}

function useStoryPlay(block: RegionStoryBlock, geometry: StoryGeometry | null, watched: RefObject<HTMLDivElement | null>): StoryPlay {
  const stops = useMemo(() => storyStops(block.steps, geometry?.entries ?? NO_ENTRIES), [block.steps, geometry]);
  const beat = useCallback((at: number) => stopBeat(stops, at), [stops]);
  const drawn = Boolean(geometry?.river);
  const play = usePlayInView(drawn ? stops.length : 1, block.steps.length, watched, beat);
  const flow = useRiverFlow(geometry?.thresholds ?? NO_THRESHOLDS, { stops, at: play.at, playing: play.playing }, drawn);
  return { play, drawn, flow };
}

export function storyFocus(block: RegionStoryBlock, geometry: StoryGeometry | null, passed: number, play: Pick<PlayInView, "at" | "choose">): { focus: StageFocus; step: number | null } {
  const fractions = geometry?.fractions ?? block.steps.map(() => ALL_PASSED);
  const step = play.at >= 0 && play.at < block.steps.length ? play.at : null;
  const focus: StageFocus = {
    district: step === null ? null : block.steps[step].districtLgd,
    stretch: step !== null,
    reached: fractions.map((fraction) => fraction <= passed),
    onStep: play.choose
  };
  return { focus, step };
}

function StoryLocator({ block, geometry }: { block: RegionStoryBlock; geometry: StoryGeometry }) {
  const marked = useMemo(() => [...geometry.districts.values()].map((district) => district.shape), [geometry]);
  return (
    <div className={LOCATOR_INSET} data-testid="story-locator">
      <IndiaLocator marked={marked} frame={geometry.view} label={locatorLabel(block.districts)} />
    </div>
  );
}

export function StoryTools({ story, played, base }: { story: StoryLayer; played: Pick<StoryPlay, "play" | "drawn">; base: string }) {
  const { play, drawn } = played;
  if (story.offered.length === 0 && !drawn) return null;
  return (
    <div className="mb-3 flex min-w-0 flex-wrap items-center justify-between gap-3">
      <StoryLayerPicker story={story} base={base} />
      {drawn ? <PlayPauseButton playing={play.playing} motion={play.motion} onToggle={play.toggle} testId="story-play" /> : null}
    </div>
  );
}

type MapView = { geometry: StoryGeometry | null; played: StoryPlay; story: StoryLayer; focus: StageFocus; waiting: boolean };

function StoryMap({ block, shapes, basin, view }: { block: RegionStoryBlock; shapes: Remote<DistrictShape[]>; basin: Remote<RiverBasin>; view: MapView }) {
  const { geometry, played, story, focus, waiting } = view;
  const { flow, play, drawn } = played;
  const { fillOf, shown } = useStoryFill(geometry, story, flow.passed);
  const hydro = datasetRow(block.datasets, HYDRORIVERS_DATASET_CODE);
  const source = <AnswerMapSource boundary={boundaryNote(block.boundaryCaption, block.datasets)} />;
  return (
    <AnswerFigure texts={{ title: storyTitle(block), source }} className="lg:sticky lg:top-24">
      <StoryTools story={story} played={played} base={block.river ? "Water" : "Districts"} />
      {shapes.failure ? <MapRetry message="The map could not be drawn. Try again in a moment." onRetry={shapes.retry} /> : null}
      {geometry ? <RiverStage geometry={geometry} flow={flow} fillOf={fillOf} focus={focus} summary={storySummary(block)} inset={<StoryLocator block={block} geometry={geometry} />} /> : waiting && !shapes.failure ? <MapPlaceholder /> : null}
      <p role="status" className="sr-only" aria-live={play.playing ? "off" : "polite"}>
        {drawn ? storyStatus(block, play.at) : ""}
      </p>
      {geometry ? <StoryKey block={block} geometry={geometry} layered={shown !== null} /> : null}
      {basin.failure && !isGone(basin.failure) ? <MapRetry message="The river could not be drawn. Try again in a moment." onRetry={basin.retry} className="mt-3" /> : null}
      <StoryLayerReadout block={block} story={story} shown={shown} shapes={shapes} />
      {geometry?.river && hydro ? (
        <div className="mt-3">
          <DatasetCredit dataset={hydro} />
        </div>
      ) : null}
    </AnswerFigure>
  );
}

export function RegionStory({ block }: { block: RegionStoryBlock }) {
  const watched = useRef<HTMLDivElement | null>(null);
  const shapes = useRemote(loadShapes);
  const basin = useStoryBasin(block.river);
  const geometry = useMemo(() => (shapes.data ? storyGeometry(block, shapes.data, basin.data) : null), [block, shapes.data, basin.data]);
  const played = useStoryPlay(block, geometry, watched);
  const story = useStoryLayer(block.layers);
  const { focus, step } = storyFocus(block, geometry, played.flow.passed, played.play);
  const waiting = shapes.data === null || (block.river !== null && basin.data === null && basin.failure === null);
  const mapped = geometry !== null || waiting || shapes.failure !== null;
  return (
    <div ref={watched} className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)] lg:items-start lg:gap-10" data-testid="region-story" data-plays="view">
      {mapped ? <StoryMap block={block} shapes={shapes} basin={basin} view={{ geometry, played, story, focus, waiting }} /> : null}
      <StorySteps block={block} focus={focus} step={step} />
    </div>
  );
}
