import { FACES_HREF, FACES_PRECEDENCE, faceFiles, faceRules } from "@/lib/pageFaces";

import { FacePreloads } from "./FacePreloads";
import { FIRST_SCREEN_FACES } from "./latinFonts";

export function FirstScreenFaces() {
  return (
    <>
      <style href={FACES_HREF} precedence={FACES_PRECEDENCE}>
        {faceRules(FIRST_SCREEN_FACES)}
      </style>
      <FacePreloads paths={faceFiles(FIRST_SCREEN_FACES)} />
    </>
  );
}
