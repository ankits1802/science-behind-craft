import { aiVideoShape } from "@/lib/componentSpecsPlates";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { parseShape } from "@/lib/shape";

import { HeldText } from "./HeldText";
import { AiTag, DownloadIcon, PAUSE_ICON_MARKUP, PLAY_ICON_MARKUP, PlayIcon } from "./KitIcons";
import { playerTime, videoMeta } from "./mediaCopy";
import { SpecDrawing } from "./SpecDrawing";

export function AiVideoView({ spec, renderUnit }: ComponentViewProps) {
  const video = parseShape(aiVideoShape, spec);
  const playback = video.playback;
  return (
    <figure className="ai ai-only" data-sec={video.section} data-kind="video" id="vid">
      <div className="ai-art">
        <SpecDrawing element={video.art} />
        <p className="vid-phase" id="vid-phase">
          {renderUnit(video.phase)}
        </p>
        <div className="vid-ctl">
          <button className="vid-play" type="button" id="vid-play" aria-label="Play the video" data-play={PLAY_ICON_MARKUP} data-pause={PAUSE_ICON_MARKUP}>
            <PlayIcon />
          </button>
          <input className="vid-range" type="range" id="vid-range" min={0} max={playback.durationMs} step={playback.stepMs} defaultValue={playback.restMs} aria-label="Video position" />
          <span className="vid-time" id="vid-time">
            {playerTime(playback.restMs, playback.durationMs)}
          </span>
        </div>
      </div>
      <AiTag label="AI video" />
      <figcaption className="ai-cap">
        <span>
          <HeldText nodes={video.caption} />
        </span>
        <span className="meta">{videoMeta(playback.durationMs, video.made)}</span>
        <button className="dl" type="button" data-dl-video={video.downloadKey} data-name={video.downloadName}>
          <DownloadIcon />
          Download
        </button>
      </figcaption>
    </figure>
  );
}
