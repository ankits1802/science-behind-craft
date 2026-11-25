import type { DocumentLanguageCode } from "@/lib/documentLanguages";
import { ENGLISH, type MonographDocument } from "@/lib/monographDocument";
import { checkedDocumentRest, checkedShellRest, documentDigest, type DocumentRest, type RestAddress, type ShellRest } from "@/lib/monographRenderShell";

export const REST_UNREAD = "The rest of this monograph could not be read. Reload the page to try again.";

export type DocumentReader = (language: DocumentLanguageCode | null, version: number | null) => Promise<MonographDocument | null>;
export type RestFetcher = (src: string) => Promise<Response>;

export function namesDocument(document: MonographDocument, address: RestAddress): boolean {
  return document.version === address.version && (address.digest === null || documentDigest(document) === address.digest);
}

export function laterDocument(current: MonographDocument | null, address: RestAddress): MonographDocument | null {
  return current !== null && current.version > address.version ? current : null;
}

export async function addressedDocument(read: DocumentReader, address: RestAddress): Promise<MonographDocument | null> {
  const current = await read(address.language, null);
  const named = current !== null && namesDocument(current, address) ? current : await read(address.language, address.version);
  const found = named ?? laterDocument(current, address);
  return found !== null && found.language === (address.language ?? ENGLISH) ? found : null;
}

async function restResponse(fetcher: RestFetcher, src: string): Promise<unknown> {
  const response = await fetcher(src);
  if (!response.ok) throw new Error(`${REST_UNREAD} (${response.status})`);
  return response.json();
}

export async function fetchedShellRest(fetcher: RestFetcher, src: string, version: number): Promise<ShellRest> {
  return checkedShellRest(await restResponse(fetcher, src), version);
}

export async function fetchedDocumentRest(fetcher: RestFetcher, src: string, version: number): Promise<DocumentRest> {
  return checkedDocumentRest(await restResponse(fetcher, src), version);
}
