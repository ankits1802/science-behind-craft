import { ComponentSlot } from "@/components/monograph/ComponentSlot";
import { UnitView } from "@/components/monograph/UnitView";
import type { MonographDocument } from "@/lib/monographDocument";
import { pieceRefs, runKey } from "@/lib/monographNotes";
import type { PassageAside, PassagePiece } from "@/lib/monographRenderLayout";

export const BESIDE_CLASS = "margin-plate";
export const BESIDE_NOTE_CLASS = "kv-beside-note";

export function runAsides(runs: readonly (readonly PassagePiece[])[], asides: readonly PassageAside[]): Map<string, PassageAside[]> {
  const found = new Map<string, PassageAside[]>();
  if (!runs.length) return found;
  for (const aside of asides) {
    const run = runs.find((held) => held.some((piece) => pieceRefs(piece).includes(aside.after))) ?? runs[runs.length - 1];
    found.set(runKey(run), [...(found.get(runKey(run)) ?? []), aside]);
  }
  return found;
}

export function BesideItems({ document, asides }: { document: MonographDocument; asides: readonly PassageAside[] | undefined }) {
  if (!asides?.length) return null;
  const { units, sources } = document.content;
  return (
    <>
      {asides.map((aside) => (
        <div className={BESIDE_CLASS} key={aside.ref} data-beside={aside.kind}>
          {aside.kind === "component" ? <ComponentSlot document={document} label={aside.ref} beside /> : <UnitView unit={units[aside.ref]} sources={sources} as="p" className={BESIDE_NOTE_CLASS} />}
        </div>
      ))}
    </>
  );
}
