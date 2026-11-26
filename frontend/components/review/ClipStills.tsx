"use client";

import { useState } from "react";

import { clipStillHref } from "@/lib/codedClips";
import { clipFilms, type ClipFilm, type CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";

export const CLIP_STILL_MISSING = "Its still could not be shown; on paper the clip keeps its credit line alone.";

function ClipStill({ film, alt }: { film: ClipFilm; alt: string }) {
  const [missing, setMissing] = useState(false);
  return (
    <figure className="grid gap-1" data-clip-still={film.clip}>
      {missing ? (
        <p className="font-ui text-label text-ink-2">{CLIP_STILL_MISSING}</p>
      ) : (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element -- the API's JPEG still, nothing for next/image to optimise */}
          <img src={clipStillHref(film.clip)} alt={alt} loading="lazy" decoding="async" onError={() => setMissing(true)} className="block h-auto w-full rounded-plate border border-rule bg-sunk" />
        </>
      )}
      {film.credit ? <figcaption className="font-ui text-caption text-ink-3">{film.credit}</figcaption> : null}
    </figure>
  );
}

export function ClipStills({ figure, alt }: { figure: Pick<CodedFigureSpec, "films">; alt: string }) {
  const films = clipFilms(figure);
  if (!films.length) return null;
  return (
    <div className="grid gap-3" data-clip-stills="">
      {films.map((film) => (
        <ClipStill key={film.key} film={film} alt={alt} />
      ))}
    </div>
  );
}
