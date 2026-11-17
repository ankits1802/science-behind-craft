"use client";

import { useCallback, useEffect, useRef } from "react";

import type { Film } from "@/components/answer/film/useFilm";
import { ListenAudio } from "@/components/answer/ListenAudio";
import type { FilmScore, ScoreCue, ScoreMusic } from "@/lib/filmScore";
import { sceneTrack } from "@/lib/filmScenes";
import { applyLevel, bedDrifted, bedTime, cueDue, filmLevels, sceneCue, type FilmMix, type SoundLevel } from "@/lib/filmSound";

function ignoreRefusedPlay(): void {}

function MusicBed({ music, playing, level, elapsed }: { music: ScoreMusic; playing: boolean; level: SoundLevel; elapsed: number }) {
  const ref = useRef<HTMLAudioElement | null>(null);
  const { volume, muted } = level;
  useEffect(() => {
    const audio = ref.current;
    if (!audio) return;
    applyLevel(audio, { volume, muted });
    if (bedDrifted(audio.currentTime, elapsed, music.durationSeconds)) audio.currentTime = bedTime(elapsed, music.durationSeconds);
    if (playing && audio.paused) audio.play().catch(ignoreRefusedPlay);
    if (!playing && !audio.paused) audio.pause();
  }, [playing, volume, muted, elapsed, music.durationSeconds]);
  return <audio ref={ref} src={music.audioUrl} loop preload="auto" className="hidden" data-testid="film-music" />;
}

function SceneCue({ cue, time, playing, level }: { cue: ScoreCue; time: number; playing: boolean; level: SoundLevel }) {
  const ref = useRef<HTMLAudioElement | null>(null);
  const fired = useRef(false);
  const { volume, muted } = level;
  useEffect(() => {
    const audio = ref.current;
    if (!audio) return;
    applyLevel(audio, { volume, muted });
    if (!playing) {
      if (!audio.paused) audio.pause();
      return;
    }
    const resumes = fired.current && audio.paused && !audio.ended && audio.currentTime > 0;
    if ((!fired.current && cueDue(cue, time)) || resumes) {
      fired.current = true;
      audio.play().catch(ignoreRefusedPlay);
    }
  }, [cue, time, playing, volume, muted]);
  return <audio ref={ref} src={cue.audioUrl} preload="auto" className="hidden" data-testid="film-cue" />;
}

export function FilmSound({ film, score, mix, onBroken }: { film: Film; score: FilmScore | null; mix: FilmMix; onBroken: () => void }) {
  const { clock, scene, send } = film;
  const playing = film.load === "ready" && clock.playing && !clock.ended;
  const current = scene ? sceneTrack(scene, clock.time) : null;
  const cue = scene ? sceneCue(score, scene.block.id) : null;
  const onRefused = useCallback(() => send({ type: "pause" }), [send]);
  const levels = filmLevels(mix, film.elapsed, film.total);
  return (
    <>
      {current && film.load === "ready" ? (
        <ListenAudio
          key={`${clock.scene}:${clock.take}:${current.at}`}
          src={current.track.audioUrl}
          playing={playing}
          rate={1}
          muted={mix.muted}
          onTime={(time) => send({ type: "heard", scene: clock.scene, time: current.start + time })}
          onEnded={() => send({ type: "trackEnded", scene: clock.scene, time: current.start + current.track.durationSeconds })}
          onBroken={onBroken}
          onRefused={onRefused}
        />
      ) : null}
      {score?.music ? <MusicBed music={score.music} playing={playing} level={levels.bed} elapsed={film.elapsed} /> : null}
      {cue ? <SceneCue key={`${clock.scene}:${clock.take}`} cue={cue} time={clock.time} playing={playing} level={levels.cue} /> : null}
    </>
  );
}
