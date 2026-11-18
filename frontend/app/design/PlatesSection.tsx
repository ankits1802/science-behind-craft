"use client";

import { useState } from "react";

import { Demo, Grid, Section } from "@/app/design/DesignParts";
import { BLOCK_CARVING, GREEN_TO_BLUE, LEUCO, NUMBERS, PHULKARI_NAME, SOURCES_BY_ID, SWAMIMALAI_NAME } from "@/app/design/fixtures";
import { ChapterRail } from "@/components/editorial/ChapterRail";
import { Cite } from "@/components/editorial/CitationCluster";
import { FactGrid } from "@/components/editorial/FactGrid";
import { Plate } from "@/components/editorial/Plate";
import { TypographicPlate, type PlateMaterial } from "@/components/editorial/TypographicPlate";
import { Figure } from "@/components/ui/Figure";
import { Tabs } from "@/components/ui/Tabs";
import type { NativeName } from "@/lib/editorialText";

type ShownPlate = { material: PlateMaterial; name: string; kicker: string | null; state: string; native?: NativeName; tags: string[] };

const PLATES: ShownPlate[] = [
  { material: "textile", name: "Kutch Bandhani", kicker: null, state: "Gujarat", tags: ["Monograph", "GI"] },
  { material: "textile", name: "Phulkari", kicker: "Embroidery", state: "Punjab", native: PHULKARI_NAME, tags: ["GI"] },
  { material: "metal", name: "Swamimalai Bronze Icons", kicker: "Bronze", state: "Tamil Nadu", native: SWAMIMALAI_NAME, tags: ["GI"] },
  { material: "stone", name: "Agra Marble Inlay", kicker: "Inlay", state: "Uttar Pradesh", tags: ["Monograph"] },
  { material: "paper", name: "Kalpi Handmade Paper", kicker: "Paper", state: "Uttar Pradesh", tags: ["GI"] },
  { material: "leather", name: "Kolhapuri Chappal", kicker: "Footwear", state: "Maharashtra", tags: ["GI"] },
  { material: "wood", name: "Channapatna Toys", kicker: "Lacquer", state: "Karnataka", tags: ["GI"] },
  { material: "fibre", name: "Sikki Grass Craft", kicker: "Grass", state: "Bihar", tags: ["GI"] },
  { material: "clay", name: "Khurja Pottery", kicker: "Pottery", state: "Uttar Pradesh", tags: ["GI"] },
  { material: "paint", name: "Madhubani Painting", kicker: "Painting", state: "Bihar", tags: ["GI"] },
  { material: "instr", name: "Thanjavur Veena", kicker: "Strings", state: "Tamil Nadu", tags: ["GI"] },
  { material: "toys", name: "Kondapalli Toys", kicker: "Toys", state: "Andhra Pradesh", tags: ["GI"] }
];

function Strip({ plate }: { plate: ShownPlate }) {
  return (
    <>
      <span className="font-reading text-[0.96875rem] leading-[1.3] font-medium">{plate.name}</span>
      <span className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1 font-ui text-caption text-ink-3">
        <span>{plate.state}</span>
        <span className="flex gap-1">
          {plate.tags.map((tag) => (
            <span key={tag} className="kv-tag">
              {tag}
              {tag === "GI" ? <span className="sr-only"> registered</span> : null}
            </span>
          ))}
        </span>
      </span>
    </>
  );
}

const CHAPTERS = [
  { id: "plates", label: "Plates" },
  { id: "label", label: "Specimen label" },
  { id: "citations", label: "Citations" },
  { id: "evidence", label: "Evidence" },
  { id: "status", label: "Status" }
];

function StarDiagram() {
  return (
    <svg viewBox="0 0 320 120" role="img" aria-label="Alum printed as pa turns red in the madder bath; lime outlines stay white" className="w-full max-w-[28rem]">
      <rect x="1" y="1" width="150" height="118" fill="var(--raised)" stroke="var(--ink-1)" />
      <rect x="169" y="1" width="150" height="118" fill="var(--raised)" stroke="var(--ink-1)" />
      <path d="M76 22 L84 50 L112 60 L84 70 L76 98 L68 70 L40 60 L68 50 Z" fill="var(--dye-madder)" />
      <path d="M244 22 L252 50 L280 60 L252 70 L244 98 L236 70 L208 60 L236 50 Z" fill="none" stroke="var(--dye-pink-edge)" strokeWidth="2" />
    </svg>
  );
}

export function PlatesSection() {
  const [tab, setTab] = useState("profile");
  return (
    <Section id="plates" title="Plates, figures and facts" lede="Photographs are plates, caption first and credit after. Drawings and charts are figures, numbered through a page. Every craft has a plate on its material's ground.">
      <Grid>
        <Demo caption="Plate: opens larger">
          <Plate src={BLOCK_CARVING.src} alt={BLOCK_CARVING.alt} ratio="3 / 2" focal={[0.1, 0.3, 0.8, 0.5]} caption="A printing block being carved in Jaipur: look at the roundels and floral sprays standing in relief. Not an ajrakh block." credit={`Photo: ${BLOCK_CARVING.credit}, via Wikimedia Commons`} />
        </Demo>
        <Demo caption="Figure: numbered, titled">
          <Figure number={3} kind="diagram" title="Red: alum, then madder" dek="Alum printed as pa turns red in the madder bath; lime outlines stay white." source="Drawn from the cited sentences; the ground is left undyed to isolate the mordant." table={<p className="font-ui text-ui font-normal text-ink-2">Before rang: alum and lime. After rang: red where alum was printed, white under lime.</p>} valueCount={2}>
            <StarDiagram />
          </Figure>
        </Demo>
      </Grid>
      <Demo caption="Collection plates, every material">
        <div className="grid grid-cols-[repeat(auto-fill,minmax(11.25rem,1fr))] gap-3">
          {PLATES.map((plate) => (
            <TypographicPlate key={plate.name} material={plate.material} englishName={plate.name} nativeName={plate.native} kicker={plate.kicker} strip={<Strip plate={plate} />} />
          ))}
        </div>
      </Demo>
      <Demo caption="Fact grid">
        <FactGrid
          facts={[
            { label: "Centres", value: <span className="kv-sentence" data-cite-host="">Ajrakhpur, Dhamadka and Khavda in Kachchh<Cite citations={GREEN_TO_BLUE.slice(1)} numbers={NUMBERS} sourcesById={SOURCES_BY_ID} /></span> },
            { label: "Colours", value: <span className="kv-sentence" data-cite-host="">Blue, black, red and white<Cite citations={GREEN_TO_BLUE} numbers={NUMBERS} sourcesById={SOURCES_BY_ID} /></span> },
            { label: "Dyes and mordants", value: <span className="kv-sentence" data-cite-host="">Indigo, madder, iron black on myrobalan, alum<Cite citations={LEUCO.slice(0, 2)} numbers={NUMBERS} sourcesById={SOURCES_BY_ID} /></span> }
          ]}
        />
      </Demo>
      <Demo caption="Chapter rail and tabs">
        <ChapterRail chapters={CHAPTERS} label="Chapters of this page" />
        <div className="mt-6">
          <Tabs label="Settings" value={tab} onChange={setTab} items={[{ value: "profile", label: "Profile", panel: <p className="font-ui text-ui font-normal text-ink-2">Tabs switch views of one object on signed-in tool pages.</p> }, { value: "preferences", label: "Preferences", panel: <p className="font-ui text-ui font-normal text-ink-2">Theme, contrast, text size and motion.</p> }, { value: "keys", label: "API keys", panel: <p className="font-ui text-ui font-normal text-ink-2">Keys for the model providers.</p> }]} />
        </div>
      </Demo>
    </Section>
  );
}
