import type { ReactNode } from "react";

import type { EventCard, TimelineAxis, TimelineEvent } from "@/lib/componentSpecsData";

import { TextLines } from "./DataParts";

type RenderUnit = (ref: string) => ReactNode;

export function axisEventName(event: TimelineEvent): string {
  return `${event.when}, ${event.title}`;
}

export function pickName(event: TimelineEvent): string {
  return `Show ${event.title} on the map`;
}

export function EventCardBody({ card, renderUnit }: { card: EventCard; renderUnit: RenderUnit }) {
  return (
    <>
      <p className="when">{renderUnit(card.when)}</p>
      <h3>{renderUnit(card.title)}</h3>
      <TextLines lines={card.lines} renderUnit={renderUnit} />
    </>
  );
}

export function TimelineAxisView({ axis, events, rest }: { axis: TimelineAxis; events: TimelineEvent[]; rest: number }) {
  return (
    <div className="tl-axis" data-axis="">
      <span className="ax-line"></span>
      {axis.breaks.map((left) => (
        <span key={left} className="ax-break" style={{ left }} aria-hidden="true"></span>
      ))}
      {axis.ticks.map((tick) => (
        <span key={tick.left} className="tick" style={{ left: tick.left }} aria-hidden="true">
          {tick.text}
        </span>
      ))}
      {axis.spans.map((span) => (
        <span key={span.left} className="span" style={{ left: span.left, width: span.width }} aria-hidden="true"></span>
      ))}
      <div className="ev-row" role="toolbar" aria-label={axis.label} aria-orientation="horizontal">
        {axis.events.map((mark, index) => (
          <button
            key={index}
            type="button"
            className={`ev r${mark.row}`}
            data-ev={index}
            aria-pressed={index === rest ? "true" : "false"}
            tabIndex={index === rest ? 0 : -1}
            style={{ left: mark.left }}
            aria-label={axisEventName(events[index])}
          >
            <span className="ln">{mark.short}</span>
            <span className="d" aria-hidden="true"></span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function TimelineListView({ items, events, rest, renderUnit }: { items: EventCard[]; events: TimelineEvent[]; rest: number; renderUnit: RenderUnit }) {
  return (
    <ol className="tl-list" data-list="">
      {items.map((item, index) => (
        <li key={index} className={index === rest ? "tl-li is-on" : "tl-li"} data-li={index} aria-current={index === rest ? "step" : undefined}>
          <button type="button" className="tl-pick" data-ev={index} aria-pressed={index === rest ? "true" : "false"} aria-label={pickName(events[index])}></button>
          <EventCardBody card={item} renderUnit={renderUnit} />
        </li>
      ))}
    </ol>
  );
}
