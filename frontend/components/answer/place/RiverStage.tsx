"use client";

import { motion, useTransform } from "framer-motion";

import type { PlacedBadge, StoryGeometry, StoryRiver } from "@/components/answer/place/storyGeometry";
import type { RiverFlow } from "@/components/answer/place/useRiverFlow";
import { DistrictFills, DistrictOutlines, type DistrictFill } from "@/components/map/DistrictLayer";
import { indiaOutlinePath } from "@/components/map/projection";
import { pointAlong, viewPercent, type View } from "@/lib/riverGeometry";
import { cn } from "@/lib/utils";

const RIVER_WIDTH = 0.007;
const SOURCE_RADIUS = 0.009;

export type StageFocus = { district: number | null; stretch: boolean; reached: readonly boolean[]; onStep: (index: number) => void };

function tributaryWidth(order: number): number {
  return 0.0012 + order * 0.0006;
}

function WaterFront({ river, flow, radius }: { river: StoryRiver; flow: RiverFlow; radius: number }) {
  const { points, lengths } = river.course;
  const cx = useTransform(flow.progress, (value) => pointAlong(points, lengths, value)[0]);
  const cy = useTransform(flow.progress, (value) => pointAlong(points, lengths, value)[1]);
  const opacity = useTransform(flow.progress, [0, 0.02, 0.97, 1], [0, 1, 1, 0]);
  return <motion.circle cx={cx} cy={cy} r={radius} style={{ opacity }} className="fill-errand-700 stroke-card dark:fill-errand-200" strokeWidth={radius * 0.4} />;
}

function RiverLines({ river, flow, view, stretch }: { river: StoryRiver; flow: RiverFlow; view: View; stretch: string | null }) {
  const width = view.width * RIVER_WIDTH;
  const course = { d: river.d, className: "stroke-errand-600 dark:stroke-errand-400", strokeWidth: width, "data-testid": "river-course" };
  const [source] = river.course.points;
  const outlet = river.course.points[river.course.points.length - 1];
  const radius = view.width * SOURCE_RADIUS;
  return (
    <g fill="none" strokeLinecap="round" strokeLinejoin="round" className="pointer-events-none">
      {river.tributaries.map((line) => (
        <path key={line.order} d={line.d} className="stroke-errand-300 dark:stroke-errand-700" strokeWidth={view.width * tributaryWidth(line.order)} />
      ))}
      <path d={river.d} className="stroke-errand-100 dark:stroke-errand-900" strokeWidth={width * 2.2} />
      {flow.moving ? <motion.path {...course} data-flow="moving" style={{ pathLength: flow.progress }} /> : <path {...course} data-flow="still" />}
      {stretch ? <path d={stretch} className="stroke-errand-800 dark:stroke-errand-200" strokeWidth={width * 1.7} data-testid="river-stretch" /> : null}
      <circle cx={source[0]} cy={source[1]} r={radius} className="fill-errand-600 stroke-card dark:fill-errand-400" strokeWidth={radius * 0.4} data-testid="river-source" />
      <circle cx={outlet[0]} cy={outlet[1]} r={radius * 0.8} className="fill-card stroke-errand-600 dark:stroke-errand-400" strokeWidth={radius * 0.5} />
      {flow.moving ? <WaterFront river={river} flow={flow} radius={radius * 0.75} /> : null}
    </g>
  );
}

function StepBadgeButton({ badge, view, focus }: { badge: PlacedBadge; view: View; focus: StageFocus }) {
  const reached = focus.reached[badge.first] ?? false;
  const on = focus.district === badge.districtLgd;
  return (
    <button
      type="button"
      tabIndex={-1}
      onClick={() => focus.onStep(badge.first)}
      style={viewPercent(badge.at, view)}
      aria-label={`Step ${badge.label}`}
      data-testid="story-badge"
      data-reached={reached ? "true" : "false"}
      className={cn(
        "absolute inline-flex h-7 min-w-7 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full px-2 text-xs font-bold tabular-nums shadow-sm ring-2 transition-colors pointer-coarse:h-9 pointer-coarse:min-w-9",
        reached ? "bg-purple-700 text-white ring-card" : "bg-card text-ink-700 ring-line-200",
        on ? "ring-purple-300 dark:ring-purple-500" : null
      )}
    >
      {badge.label}
    </button>
  );
}

function PointLabel({ text, at, view }: { text: string; at: readonly [number, number]; view: View }) {
  return (
    <span style={viewPercent(at, view)} className="pointer-events-none absolute -translate-x-1/2 -translate-y-[160%] rounded-full bg-card/90 px-1.5 text-[11px] font-semibold text-errand-800 shadow-sm dark:text-errand-200">
      {text}
    </span>
  );
}

export function RiverStage({ geometry, flow, fillOf, focus, summary }: { geometry: StoryGeometry; flow: RiverFlow; fillOf: DistrictFill; focus: StageFocus; summary: string }) {
  const { view, river } = geometry;
  const focused = focus.district === null ? undefined : geometry.districts.get(focus.district);
  const stretch = focused && river && focus.stretch ? (river.stretches.get(focused.lgd) ?? null) : null;
  const points = river?.course.points ?? [];
  return (
    <div className="relative aspect-[4/3] w-full overflow-hidden rounded-md bg-field-100" data-testid="river-stage" data-passed={flow.passed}>
      <svg viewBox={`${view.x} ${view.y} ${view.width} ${view.height}`} className="absolute inset-0 h-full w-full" role="img" aria-label={summary}>
        <path d={indiaOutlinePath()} fillRule="evenodd" className="fill-card" />
        <DistrictFills shapes={geometry.context} fillOf={fillOf} />
        <path d={indiaOutlinePath()} fillRule="evenodd" className="pointer-events-none fill-none stroke-purple-300 dark:stroke-purple-800" strokeWidth={1.2} vectorEffect="non-scaling-stroke" />
        {focused ? <DistrictOutlines shapes={[focused.shape]} className="stroke-ink-900" /> : null}
        {river ? <RiverLines river={river} flow={flow} view={view} stretch={stretch} /> : null}
      </svg>
      {river && points.length > 1 ? (
        <>
          <PointLabel text="Source" at={points[0]} view={view} />
          <PointLabel text="Outlet" at={points[points.length - 1]} view={view} />
        </>
      ) : null}
      {geometry.badges.map((badge) => (
        <StepBadgeButton key={badge.districtLgd} badge={badge} view={view} focus={focus} />
      ))}
    </div>
  );
}
