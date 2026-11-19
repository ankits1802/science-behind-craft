import { createHash } from "node:crypto";

export const DNS_NAMESPACE = "6ba7b810-9dad-11d1-80b4-00c04fd430c8";
export const CRAFT_MASTER_NAME = "craft-master.kalavigyan";

function uuidBytes(uuid: string): Buffer {
  return Buffer.from(uuid.replace(/-/g, ""), "hex");
}

export function uuidV5(namespace: string, name: string): string {
  const hash = createHash("sha1").update(uuidBytes(namespace)).update(name, "utf8").digest();
  hash[6] = (hash[6] & 0x0f) | 0x50;
  hash[8] = (hash[8] & 0x3f) | 0x80;
  const hex = hash.subarray(0, 16).toString("hex");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export const CURATION_NAMESPACE = uuidV5(DNS_NAMESPACE, CRAFT_MASTER_NAME);

export function curatedClaimId(slug: string, key: string): string {
  return uuidV5(CURATION_NAMESPACE, ["curation", slug, key].join(":"));
}
