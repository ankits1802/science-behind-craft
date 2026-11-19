import { audioPlayerShape } from "@/lib/componentSpecsPlates";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

import { PlayIcon } from "./KitIcons";

export function AudioPlayerView({ spec, renderUnit }: ComponentViewProps) {
  const player = parseShape(audioPlayerShape, spec);
  return (
    <div className="end-block kv-listen-block">
      <h3 className="kv-sub-h">{renderUnit(player.title)}</h3>
      <p className="kv-sub-d">{renderUnit(player.description)}</p>
      <div className="kv-actions">
        <button className="kv-btn" type="button" data-listen-open="" aria-controls={player.playerId}>
          <PlayIcon />
          <span>
            {`${player.action} · `}
            <span data-listen-min="">{player.minutes}</span>
            {" min"}
          </span>
        </button>
      </div>
    </div>
  );
}
