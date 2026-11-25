"use client";

import { FACE_TYPE } from "@/lib/pageFaces";

export function FacePreloads({ paths }: { paths: readonly string[] }) {
  return paths.map((path) => <link key={path} rel="preload" href={path} as="font" type={FACE_TYPE} crossOrigin="anonymous" />);
}
