import { KitFigure } from "@/components/artkit/KitFigure";
import { kitIds, partIds, type KitIds } from "@/components/artkit/kitIds";
import { KitPartArt } from "@/components/artkit/KitPartArt";
import { KitTextures } from "@/components/artkit/KitTextures";
import { kitSheet, kitSheetLayouts, type SheetLayout, type SheetPart, type SheetTile } from "@/lib/artKitSheet";

function Tile({ tile, ids }: { tile: SheetTile; ids: KitIds }) {
  return (
    <li className="kv-kit-tile" data-kit-tile={tile.part.part} data-kit-specimen={tile.key}>
      <div className="kv-kit-art">
        <svg viewBox="0 0 120 120" aria-hidden="true" focusable="false">
          <KitPartArt part={tile.part} ids={partIds(ids, tile.key.replace(/[^A-Za-z0-9_-]+/g, "-"))} />
        </svg>
      </div>
      <p className="kv-kit-tile-caption">{tile.caption}</p>
    </li>
  );
}

function Tiles({ tiles, ids, label }: { tiles: SheetTile[]; ids: KitIds; label: string }) {
  if (!tiles.length) return null;
  return (
    <ul className="kv-kit-sheet-grid" aria-label={label}>
      {tiles.map((tile) => (
        <Tile key={tile.key} tile={tile} ids={ids} />
      ))}
    </ul>
  );
}

function PartSection({ part }: { part: SheetPart }) {
  const ids = kitIds(`design/kit/${part.name}`);
  return (
    <section className="grid gap-4 border-t border-ink-1 py-section" aria-labelledby={`${ids.base}-h`} data-kit-sheet-part={part.name}>
      <KitTextures ids={ids} />
      <div className="grid gap-1">
        <h2 id={`${ids.base}-h`} className="font-headline text-h2">
          {part.title}
        </h2>
        <p className="font-ui text-label text-ink-2">{part.families}</p>
      </div>
      <Tiles tiles={part.variants} ids={ids} label={`${part.title}, each form`} />
      <Tiles tiles={part.materials} ids={ids} label={`${part.title}, each depicted material`} />
    </section>
  );
}

function LayoutSection({ layout }: { layout: SheetLayout }) {
  const label = `design/kit/layout-${layout.key}`;
  return (
    <section className="grid gap-4 border-t border-rule py-8" data-kit-sheet-layout={layout.key}>
      <h3 className="font-reading text-h3">{layout.title}</h3>
      <KitFigure spec={layout.spec} label={label} renderUnit={(ref) => layout.texts[ref] ?? ""} unitText={(ref) => layout.texts[ref] ?? ""} />
    </section>
  );
}

export function KitSheet() {
  return (
    <>
      <section className="grid gap-2 border-t border-ink-1 py-section" aria-labelledby="kit-layouts-h">
        <h2 id="kit-layouts-h" className="font-headline text-h2">
          The four layouts
        </h2>
        {kitSheetLayouts().map((layout) => (
          <LayoutSection key={layout.key} layout={layout} />
        ))}
      </section>
      {kitSheet().map((part) => (
        <PartSection key={part.name} part={part} />
      ))}
    </>
  );
}
