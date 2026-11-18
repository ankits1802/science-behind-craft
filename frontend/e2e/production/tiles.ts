import { createInflate } from "node:zlib";

export const FLAT_CHANNEL_SLACK = 4;
export const FLAT_SHARE = 0.999;
export const SHORT_TILE_SHARE = 0.5;

export type TileScan = { width: number; height: number; tileHeight: number; judged: number; flat: number[] };

type Image = { width: number; height: number; channels: number; data: Buffer };
type Header = Omit<Image, "data">;

const SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const CHANNELS_BY_COLOUR_TYPE: Record<number, number> = { 2: 3, 6: 4 };
const CHUNK_FRAME_BYTES = 12;

function headerOf(body: Buffer): Header {
  const [bitDepth, colourType, , , interlace] = body.subarray(8, 13);
  const channels = CHANNELS_BY_COLOUR_TYPE[colourType];
  if (bitDepth !== 8 || !channels || interlace !== 0) {
    throw new Error(`the screenshot PNG is ${bitDepth}-bit, colour type ${colourType}, interlace ${interlace}; only 8-bit RGB or RGBA without interlace is read`);
  }
  return { width: body.readUInt32BE(0), height: body.readUInt32BE(4), channels };
}

function readPng(png: Buffer): Image {
  if (!png.subarray(0, SIGNATURE.length).equals(SIGNATURE)) throw new Error("the screenshot is not a PNG");
  const data: Buffer[] = [];
  let header: Header | null = null;
  for (let offset = SIGNATURE.length; offset + 8 <= png.length; ) {
    const length = png.readUInt32BE(offset);
    const type = png.toString("latin1", offset + 4, offset + 8);
    const body = png.subarray(offset + 8, offset + 8 + length);
    if (type === "IHDR") header = headerOf(body);
    if (type === "IDAT") data.push(body);
    offset += CHUNK_FRAME_BYTES + length;
  }
  if (!header) throw new Error("the screenshot PNG has no header");
  return { ...header, data: Buffer.concat(data) };
}

function paeth(left: number, up: number, upLeft: number): number {
  const estimate = left + up - upLeft;
  const toLeft = Math.abs(estimate - left);
  const toUp = Math.abs(estimate - up);
  const toUpLeft = Math.abs(estimate - upLeft);
  if (toLeft <= toUp && toLeft <= toUpLeft) return left;
  return toUp <= toUpLeft ? up : upLeft;
}

function unfilter(filter: number, row: Uint8Array, previous: Uint8Array, step: number): void {
  for (let index = 0; index < row.length; index += 1) {
    const left = index >= step ? row[index - step] : 0;
    const up = previous[index];
    if (filter === 1) row[index] = (row[index] + left) & 0xff;
    else if (filter === 2) row[index] = (row[index] + up) & 0xff;
    else if (filter === 3) row[index] = (row[index] + ((left + up) >> 1)) & 0xff;
    else if (filter === 4) row[index] = (row[index] + paeth(left, up, index >= step ? previous[index - step] : 0)) & 0xff;
    else if (filter !== 0) throw new Error(`the screenshot PNG uses unknown filter ${filter}`);
  }
}

class Rows {
  count = 0;
  private previous: Uint8Array;
  private row: Uint8Array;
  private filled = -1;
  private filter = 0;

  constructor(
    private readonly stride: number,
    private readonly channels: number
  ) {
    this.previous = new Uint8Array(stride);
    this.row = new Uint8Array(stride);
  }

  take(chunk: Buffer, onRow: (row: Uint8Array) => void): void {
    for (let offset = 0; offset < chunk.length; ) {
      if (this.filled < 0) {
        this.filter = chunk[offset];
        this.filled = 0;
        offset += 1;
        continue;
      }
      const taken = Math.min(this.stride - this.filled, chunk.length - offset);
      this.row.set(chunk.subarray(offset, offset + taken), this.filled);
      this.filled += taken;
      offset += taken;
      if (this.filled < this.stride) continue;
      unfilter(this.filter, this.row, this.previous, this.channels);
      onRow(this.row);
      [this.previous, this.row] = [this.row, this.previous];
      this.filled = -1;
      this.count += 1;
    }
  }
}

class Tiles {
  readonly scan: TileScan;
  private index = 0;
  private reference: number[] | null = null;
  private matching = 0;
  private pixels = 0;
  private rows = 0;

  constructor(
    image: Header,
    tileHeight: number,
    private readonly channels: number
  ) {
    this.scan = { width: image.width, height: image.height, tileHeight, judged: 0, flat: [] };
  }

  add(row: Uint8Array): void {
    this.reference ??= [row[0], row[1], row[2]];
    const [red, green, blue] = this.reference;
    for (let index = 0; index < row.length; index += this.channels) {
      const near =
        Math.abs(row[index] - red) <= FLAT_CHANNEL_SLACK && Math.abs(row[index + 1] - green) <= FLAT_CHANNEL_SLACK && Math.abs(row[index + 2] - blue) <= FLAT_CHANNEL_SLACK;
      if (near) this.matching += 1;
    }
    this.pixels += row.length / this.channels;
    this.rows += 1;
    if (this.rows === this.scan.tileHeight) this.close();
  }

  close(): void {
    if (this.rows > 0 && this.rows >= this.scan.tileHeight * SHORT_TILE_SHARE) {
      this.scan.judged += 1;
      if (this.matching >= this.pixels * FLAT_SHARE) this.scan.flat.push(this.index);
    }
    this.index += 1;
    this.reference = null;
    this.matching = 0;
    this.pixels = 0;
    this.rows = 0;
  }
}

export async function scanTiles(png: Buffer, tileHeight: number): Promise<TileScan> {
  if (!Number.isInteger(tileHeight) || tileHeight < 1) throw new Error(`a tile must be a whole number of rows, not ${tileHeight}`);
  const image = readPng(png);
  const rows = new Rows(image.width * image.channels, image.channels);
  const tiles = new Tiles(image, tileHeight, image.channels);
  const inflater = createInflate();
  inflater.end(image.data);
  for await (const chunk of inflater as AsyncIterable<Buffer>) rows.take(chunk, (row) => tiles.add(row));
  if (rows.count !== image.height) throw new Error(`the screenshot PNG holds ${rows.count} of its ${image.height} rows`);
  tiles.close();
  return tiles.scan;
}
