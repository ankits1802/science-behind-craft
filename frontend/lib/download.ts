import { API_BASE, ApiError, describeApiBody, statusFallback } from "@/lib/api";

const REVOKE_AFTER_MS = 1000;
const NAMED_UTF8 = /filename\*\s*=\s*utf-8''([^;]+)/i;
const NAMED_PLAIN = /filename\s*=\s*"?([^";]+)"?/i;
const UNNAMED_STATUS = 502;

export function saveBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), REVOKE_AFTER_MS);
}

export async function downloadFile(url: string, fileName: string): Promise<void> {
  const response = await fetch(url, { cache: "no-store", credentials: "omit" });
  if (!response.ok) throw new Error(`downloading ${fileName} answered ${response.status}`);
  saveBlob(await response.blob(), fileName);
}

function decoded(value: string): string | null {
  try {
    return decodeURIComponent(value);
  } catch (error) {
    if (error instanceof URIError) return null;
    throw error;
  }
}

export function dispositionFileName(header: string | null): string | null {
  if (!header) return null;
  const encoded = NAMED_UTF8.exec(header);
  const utf8 = encoded ? decoded(encoded[1].trim()) : null;
  if (utf8) return utf8;
  const plain = NAMED_PLAIN.exec(header.replace(NAMED_UTF8, ""));
  const name = plain?.[1].trim() ?? "";
  return name || null;
}

async function failedBody(response: Response): Promise<unknown> {
  const type = response.headers.get("content-type") ?? "";
  return type.includes("application/json") ? response.json().catch(() => null) : null;
}

export async function downloadApiFile(path: string, failure: string): Promise<string> {
  const response = await fetch(`${API_BASE}/api${path}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await failedBody(response);
    throw new ApiError(response.status, describeApiBody(body, statusFallback(response.status, failure)), body, response.headers);
  }
  const name = dispositionFileName(response.headers.get("content-disposition"));
  if (!name) throw new ApiError(UNNAMED_STATUS, failure, null, response.headers);
  saveBlob(await response.blob(), name);
  return name;
}
