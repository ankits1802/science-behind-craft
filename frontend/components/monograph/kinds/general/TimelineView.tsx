"use client";

import { useId, useMemo, useRef } from "react";

import { TimelineTrack, type TrackPoint } from "@/components/answer/journey/TimelineTrack";
import { usePlayInView } from "@/components/motion/usePlayInView";
import { GeneralFigure, type RenderUnit } from "@/components/monograph/kinds/general/GeneralFigure";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { eraYear, parsedSpec, timelineSpecShape, type TimelineEvent } from "@/lib/componentSpecsGeneral";
import { pointPositions, timelineBeat } from "@/lib/timelinePlay";
import { cn } from "@/lib/utils";

const POINTS_LABEL = "Dated moments";

function trackPoints(events: readonly TimelineEvent[], renderUnit: RenderUnit, textOf: (ref: string) => string): TrackPoint[] {
  const positions = pointPositions(events.map((event) => event.year));
  return events.map((event, at) => {
    const title = textOf(event.title);
    return { key: `${event.year}-${at}`, position: positions[at], name: title ? `${eraYear(event.year)}, ${title}` : eraYear(event.year), shown: renderUnit(event.when) };
  });
}

function Played({ events, renderUnit, textOf }: { events: TimelineEvent[]; renderUnit: RenderUnit; textOf: (ref: string) => string }) {
  const watched = useRef<HTMLDivElement | null>(null);
  const play = usePlayInView(events.length, events.length - 1, watched, timelineBeat);
  const points = useMemo(() => trackPoints(events, renderUnit, textOf), [events, renderUnit, textOf]);
  return (
    <div className="grid gap-3" ref={watched} data-testid="general-timeline-play" data-at={play.at}>
      <TimelineTrack points={points} play={play} label={POINTS_LABEL} first={eraYear(events[0].year)} last={eraYear(events[events.length - 1].year)} />
      <ol className="grid" data-testid="general-timeline">
        {events.map((event, at) => {
          const current = at === play.at;
          return (
            <li
              key={`${event.year}-${at}`}
              aria-current={current ? "step" : undefined}
              className={cn("grid gap-x-4 gap-y-1 border-t border-s-2 border-t-rule py-3 ps-3 transition-colors duration-state sm:grid-cols-[7rem_minmax(0,1fr)]", current ? "border-s-ink-1" : "border-s-transparent")}
            >
              <p className="font-ui text-label font-semibold text-ink-1 [font-variant-numeric:lining-nums_tabular-nums]">{renderUnit(event.when)}</p>
              <div className="grid min-w-0 gap-1">
                <p className="font-ui text-h4 text-ink-1">{renderUnit(event.title)}</p>
                <p className="max-w-measure font-reading text-body-sm text-ink-1">{renderUnit(event.text)}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function TimelineView({ spec, renderUnit, unitText }: ComponentViewProps) {
  const timeline = useMemo(() => parsedSpec(timelineSpecShape, spec), [spec]);
  const titleId = useId();
  const textOf = useMemo(() => unitText ?? (() => ""), [unitText]);
  if (!timeline) return null;
  return (
    <GeneralFigure kind="timeline" head={timeline.head} titleId={titleId} renderUnit={renderUnit}>
      <Played events={timeline.events} renderUnit={renderUnit} textOf={textOf} />
    </GeneralFigure>
  );
}
