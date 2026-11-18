"use client";

import { Demo, Grid, Section } from "@/app/design/DesignParts";
import { GREEN_TO_BLUE, LEUCO, NUMBERS, SOURCES_BY_ID } from "@/app/design/fixtures";
import { Cite } from "@/components/editorial/CitationCluster";
import { MarginNotes, Spread } from "@/components/editorial/MarginNotes";
import { SourcePanel } from "@/components/editorial/SourcePanel";
import { clusterEntries } from "@/lib/citationCluster";
import { marginNotes } from "@/lib/marginNotes";

const SENTENCES = [
  { anchorId: "demo-sentence-green", citations: GREEN_TO_BLUE, text: "Cloth lifted from the indigo vat is bright green at first and turns blue as oxygen meets the dye on the fibres." },
  { anchorId: "demo-sentence-leuco", citations: LEUCO, text: "Indigo is insoluble in water, so the vat reduces it to a soluble leuco form, leucoindigo, which enters the fibre and oxidises back to insoluble blue in the air." }
];

const NOTES = marginNotes(
  SENTENCES.map((sentence) => ({ anchorId: sentence.anchorId, sourceIds: sentence.citations.map((citation) => citation.sourceId) })),
  NUMBERS,
  SOURCES_BY_ID
);

function CitedParagraph() {
  return (
    <p className="font-reading text-body text-ink-1">
      {SENTENCES.map((sentence) => (
        <span key={sentence.anchorId}>
          <span id={sentence.anchorId} className="kv-sentence" data-cite-host="">
            {sentence.text}
            <Cite citations={sentence.citations} numbers={NUMBERS} sourcesById={SOURCES_BY_ID} />
          </span>{" "}
        </span>
      ))}
    </p>
  );
}

export function CitationSection() {
  const entries = clusterEntries(GREEN_TO_BLUE, NUMBERS, SOURCES_BY_ID);
  return (
    <Section
      id="citations"
      title="Citations"
      lede="One cluster of numerals per sentence, de-duplicated by source and sorted. It opens every quote behind the sentence: a popover from 640px, docked in the margin from 1200px, a bottom sheet on a phone."
    >
      <Demo caption="In the text, live: press a numeral">
        <Spread margin={<MarginNotes notes={NOTES} />}>
          <CitedParagraph />
        </Spread>
      </Demo>
      <Grid>
        <Demo caption="Popover, open">
          <div className="kv-pop max-w-full">
            <SourcePanel entries={entries} headingId="demo-popover-heading" onClose={() => undefined} />
          </div>
        </Demo>
        <Demo caption="Bottom sheet on a phone, open">
          <div className="mx-auto w-full max-w-[22rem] overflow-hidden rounded-[2rem] border border-ink-1 bg-sunk pt-10">
            <div className="kv-sheet" data-preview="">
              <SourcePanel entries={entries} headingId="demo-sheet-heading" onClose={() => undefined} />
            </div>
          </div>
        </Demo>
      </Grid>
    </Section>
  );
}
