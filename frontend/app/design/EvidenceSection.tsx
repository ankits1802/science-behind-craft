"use client";

import type { ReactNode } from "react";

import { Section } from "@/app/design/DesignParts";
import { GREEN_TO_BLUE, HYPOTHESIS, LEUCO, NUMBERS, SOURCES_BY_ID } from "@/app/design/fixtures";
import { Cite } from "@/components/editorial/CitationCluster";
import { EvidenceTag, HypothesisText, InferredText, SourcesDifferNote } from "@/components/editorial/EvidenceMark";
import type { EvidenceState } from "@/lib/citationCluster";
import type { Citation } from "@/lib/types";

function Cited({ text, citations }: { text: string; citations: Citation[] }) {
  return (
    <span className="kv-sentence" data-cite-host="">
      {text}
      <Cite citations={citations} numbers={NUMBERS} sourcesById={SOURCES_BY_ID} />
    </span>
  );
}

function Row({ state, name, note, children }: { state: EvidenceState; name: string; note: string; children: ReactNode }) {
  return (
    <div className="grid gap-3 border-b border-rule py-4 md:grid-cols-[12rem_minmax(0,1fr)_10rem] md:gap-6">
      <p className="font-ui text-label text-ink-1">
        {name}
        <span className="mt-0.5 block font-normal text-ink-3">{note}</span>
      </p>
      <div className="font-reading text-body text-ink-1">{children}</div>
      <div>
        <EvidenceTag state={state} />
      </div>
    </div>
  );
}

export function EvidenceSection() {
  return (
    <Section id="evidence" title="Evidence states" lede="Each state has a word, so none relies on colour. A page states its norm once; a mark appears only where a sentence differs from it.">
      <div className="border-t border-rule">
        <Row state="verified" name="Verified" note="Quoted and checked against the source by a second reader.">
          <Cited text="Cloth lifted from the indigo vat is bright green at first and turns blue as oxygen meets the dye on the fibres." citations={GREEN_TO_BLUE} />
        </Row>
        <Row state="provisional" name="Provisional" note="Quoted, awaiting the second check. No mark in the text.">
          <Cited text="Indigo is insoluble in water, so the vat reduces it to a soluble leuco form." citations={LEUCO.slice(1, 3)} />
        </Row>
        <Row state="inferred" name="Inferred" note="Follows from cited sentences; no source says it in these words.">
          <InferredText>
            <Cited text="Under the clay, the alum is kept out of the indigo, so those areas can still turn red in the madder bath." citations={GREEN_TO_BLUE.slice(1, 2)} />
          </InferredText>
        </Row>
        <Row state="hypothesis" name="Hypothesis" note="A named scholar's proposal, not a finding.">
          <HypothesisText>
            <Cited text="Scholars believe the word ajrakh derives from the Arabic azrak, meaning blue." citations={HYPOTHESIS} />
          </HypothesisText>
        </Row>
        <Row state="differ" name="Sources differ" note="Two cited readings disagree; both are quoted.">
          <Cited text="A natural indigo vat of indigo, lime and seed ferments before it dyes." citations={LEUCO.slice(0, 1)} />
          <SourcesDifferNote summary="months, or about one month">
            <Cited text="One account leaves the seeds in the vat for months." citations={LEUCO.slice(2, 3)} />{" "}
            <Cited text="Another records about one month." citations={LEUCO.slice(3, 4)} />
          </SourcesDifferNote>
        </Row>
      </div>
    </Section>
  );
}
