import { createHmac } from "node:crypto";

export const TOTP_DIGITS = 6;
export const TOTP_PERIOD_SECONDS = 30;

const BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
const BYTE_BITS = 8;
const BASE32_BITS = 5;
const CARRY_MASK = 0xfff;
const LOW_WORD = 2 ** 32;

export function base32Bytes(secret: string): Buffer {
  const bytes: number[] = [];
  let carried = 0;
  let bits = 0;
  for (const char of secret.replace(/[\s=-]/g, "").toUpperCase()) {
    const index = BASE32_ALPHABET.indexOf(char);
    if (index < 0) throw new Error("the two-step secret is not base32");
    carried = ((carried << BASE32_BITS) | index) & CARRY_MASK;
    bits += BASE32_BITS;
    if (bits >= BYTE_BITS) {
      bits -= BYTE_BITS;
      bytes.push((carried >>> bits) & 0xff);
    }
  }
  return Buffer.from(bytes);
}

export function totpCode(secret: string, atMs: number): string {
  const counter = Math.floor(atMs / 1000 / TOTP_PERIOD_SECONDS);
  const message = Buffer.alloc(8);
  message.writeUInt32BE(Math.floor(counter / LOW_WORD), 0);
  message.writeUInt32BE(counter % LOW_WORD, 4);
  const mac = createHmac("sha1", base32Bytes(secret)).update(message).digest();
  const offset = mac[mac.length - 1] & 0x0f;
  const binary = mac.readUInt32BE(offset) & 0x7fffffff;
  return String(binary % 10 ** TOTP_DIGITS).padStart(TOTP_DIGITS, "0");
}
