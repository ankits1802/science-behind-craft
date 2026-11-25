import type { DocumentLanguageCode } from "@/lib/documentLanguages";
import { ENGLISH, type MonographDocument } from "@/lib/monographDocument";
import { documentDigest, type RestAddress } from "@/lib/monographRenderShell";

export type DocumentReader = (language: DocumentLanguageCode | null, version: number | null) => Promise<MonographDocument | null>;

export function namesDocument(document: MonographDocument, address: RestAddress): boolean {
  return document.version === address.version && (address.digest === null || documentDigest(document) === address.digest);
}

export async function addressedDocument(read: DocumentReader, address: RestAddress): Promise<MonographDocument | null> {
  const current = await read(address.language, null);
  const found = current !== null && namesDocument(current, address) ? current : await read(address.language, address.version);
  return found !== null && found.language === (address.language ?? ENGLISH) ? found : null;
}
