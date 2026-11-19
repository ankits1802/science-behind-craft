export const CRAFT_MONOGRAPHS: Readonly<Record<string, string>> = {
  "Kutch-Ajrakh": "/monographs/kutch-ajrakh/index.html"
};

export const ROUTER_REQUEST_HEADER = "rsc";

export function isCraftMonograph(slug: string): boolean {
  return Object.hasOwn(CRAFT_MONOGRAPHS, slug);
}

export function cameByRouter(documentPath: string | null, currentPath: string): boolean {
  return documentPath !== null && documentPath !== currentPath;
}
