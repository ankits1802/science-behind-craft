"use client";

import { useEffect, useRef } from "react";

export function ListenAudio({
  src,
  playing,
  rate,
  muted = false,
  onTime,
  onEnded,
  onBroken,
  onRefused
}: {
  src: string;
  playing: boolean;
  rate: number;
  muted?: boolean;
  onTime: (time: number) => void;
  onEnded: () => void;
  onBroken: () => void;
  onRefused: () => void;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.playbackRate = rate;
    audio.muted = muted;
    if (playing && audio.paused) audio.play().catch(onRefused);
    if (!playing && !audio.paused) audio.pause();
  }, [playing, rate, muted, src, onRefused]);

  return (
    <audio
      ref={audioRef}
      src={src}
      preload="auto"
      onTimeUpdate={(event) => onTime(event.currentTarget.currentTime)}
      onEnded={onEnded}
      onError={onBroken}
      className="hidden"
      data-testid="listen-audio"
    />
  );
}
