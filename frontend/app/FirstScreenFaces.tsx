import { FACE_TYPE, FACES_HREF, FACES_PRECEDENCE, faceFiles, faceRules } from "@/lib/pageFaces";

import { FIRST_SCREEN_FACES } from "./latinFonts";

export function FirstScreenFaces() {
  return (
    <>
      <style href={FACES_HREF} precedence={FACES_PRECEDENCE}>
        {faceRules(FIRST_SCREEN_FACES)}
      </style>
      {faceFiles(FIRST_SCREEN_FACES).map((path) => (
        <link key={path} rel="preload" href={path} as="font" type={FACE_TYPE} crossOrigin="anonymous" />
      ))}
    </>
  );
}
