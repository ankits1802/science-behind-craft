"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { RotateCcw } from "lucide-react";

import { MapPlaceholder } from "@/components/answer/place/MapPlaceholder";
import { RiverStage, type StageFocus } from "@/components/answer/place/RiverStage";
import { StoryKey, StoryLayerPicker } from "@/components/answer/place/StoryKey";
import { storyGeometry, storyTone, type StoryGeometry } from "@/components/answer/place/storyGeometry";
import { StorySteps } from "@/components/answer/place/StorySteps";
import { useRiverFlow, type RiverFlow } from "@/components/answer/place/useRiverFlow";
import { useStoryLayer, type StoryLayer } from "@/components/answer/place/useStoryLayer";
import { DatasetCredit } from "@/components/DatasetCredit";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { useRemote, type Remote } from "@/components/hooks/useRemote";
import { choroplethTone } from "@/components/map/ChoroplethLegend";
import { NO_DATA_TONE, type DistrictFill } from "@/components/map/DistrictLayer";
import { MapAttribution } from "@/components/map/MapAttribution";
import { LayerStatus } from "@/components/map/MapLayerView";
import { loadShapes, type DistrictShape } from "@/components/map/shapeGeometry";
import { RetryLine } from "@/components/RemotePanels";
import { HYDRORIVERS_DATASET_CODE, type RegionStoryBlock, type RiverPath } from "@/lib/explainerPlace";
import { boundaryNote, datasetRow, isGone } from "@/lib/placeView";
import { layerFills } from "@/lib/regionView";
import { ALL_PASSED, missingReaches, playingStep, storySummary } from "@/lib/regionStory";
import { fetchRiverBasin, type RiverBasin } from "@/lib/riverTopology";
import { ShapeError } from "@/lib/shape";

const NO_THRESHOLDS: readonly number[] = [];

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

function useStoryFill(geometry: StoryGeometry | null, story: StoryLayer, passed: number): DistrictFill {
  const data = story.layer.data;
  const fills = useMemo(() => (data ? layerFills(data) : null), [data]);
  return useCallback(
    (shape: DistrictShape) => {
      if (data && fills) {
        const index = fills.get(shape.lgd);
        return index === undefined ? NO_DATA_TONE : choroplethTone(index, data.classes.length);
      }
      return geometry ? storyTone(geometry, shape.lgd, passed) : null;
    },
    [data, fills, geometry, passed]
  );
}

function StoryTools({ story, flow, base }: { story: StoryLayer; flow: RiverFlow; base: string }) {
  if (story.offered.length === 0 && !flow.replay) return null;
  return (
    <div className="mb-3 flex min-w-0 flex-wrap items-center justify-between gap-2">
      <StoryLayerPicker story={story} base={base} />
      {flow.replay ? (
        <button type="button" onClick={flow.replay} className="field-button-secondary min-h-9 rounded-full px-3 text-xs">
          <RotateCcw className="h-3.5 w-3.5" aria-hidden />
          Replay
        </button>
      ) : null}
    </div>
  );
}

export function RegionStory({ block }: { block: RegionStoryBlock }) {
  const reduce = useAppReducedMotion();
  const shapes = useRemote(loadShapes);
  const basin = useStoryBasin(block.river);
  const geometry = useMemo(() => (shapes.data ? storyGeometry(block, shapes.data, basin.data) : null), [block, shapes.data, basin.data]);
  const expected = block.river !== null && basin.failure === null && shapes.failure === null;
  const frameRef = useRef<HTMLElement | null>(null);
  const flow = useRiverFlow(frameRef, geometry?.thresholds ?? NO_THRESHOLDS, { expected, drawn: Boolean(geometry?.river) }, reduce);
  const story = useStoryLayer(block.layers);
  const [selected, setSelected] = useState<number | null>(null);
  const fillOf = useStoryFill(geometry, story, flow.passed);
  const fractions = geometry?.fractions ?? block.steps.map(() => ALL_PASSED);
  const step = selected ?? playingStep(fractions, flow.passed);
  const focus: StageFocus = {
    district: step === null ? null : block.steps[step].districtLgd,
    stretch: selected !== null,
    reached: fractions.map((fraction) => fraction <= flow.passed),
    onStep: (index) => setSelected((current) => (current === index ? null : index))
  };
  const waiting = shapes.data === null || (block.river !== null && basin.data === null && basin.failure === null);
  const hydro = datasetRow(block.datasets, HYDRORIVERS_DATASET_CODE);
  const mapped = geometry !== null || waiting || shapes.failure !== null;

  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)] lg:items-start" data-testid="region-story">
      {mapped ? (
        <figure ref={frameRef} className="min-w-0 lg:sticky lg:top-24">
          <StoryTools story={story} flow={flow} base={block.river ? "Water" : "Districts"} />
          {shapes.failure ? <RetryLine message="Couldn't load the map." onRetry={shapes.retry} /> : null}
          {geometry ? <RiverStage geometry={geometry} flow={flow} fillOf={fillOf} focus={focus} summary={storySummary(block)} /> : waiting && !shapes.failure ? <MapPlaceholder /> : null}
          {geometry ? <StoryKey block={block} geometry={geometry} layered={story.layer.data !== null} /> : null}
          {basin.failure && !isGone(basin.failure) ? <RetryLine message="Couldn't load the river." onRetry={basin.retry} className="mt-3" /> : null}
          {story.chosen ? <LayerStatus layer={story.layer} shapes={shapes} /> : null}
          {geometry?.river && hydro ? (
            <div className="mt-3">
              <DatasetCredit dataset={hydro} />
            </div>
          ) : null}
          <MapAttribution boundary={boundaryNote(block.boundaryCaption, block.datasets)} />
        </figure>
      ) : null}
      <StorySteps block={block} focus={focus} step={step} />
    </div>
  );
}
