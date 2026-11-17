"use client";

import { CitationChips } from "@/components/answer/CitationContext";
import { EvidenceLevelBadge, EvidenceSignalBadge } from "@/components/answer/EvidenceBadge";
import { usePageClaims } from "@/components/craft/CraftClaims";
import type { EvidenceEntry, EvidenceSubject, PageClaim, PageEvidence } from "@/lib/craftPageContract";
import { entryCount, groupCount, PROVENANCE_LABEL, SUBJECT_KIND_LABEL } from "@/lib/craftPageView";
import { countNoun } from "@/lib/format";

function EvidenceClaim({ claim }: { claim: PageClaim }) {
  return (
    <p className="text-sm leading-6 text-ink-700 [overflow-wrap:anywhere]" data-level={claim.level} data-provenance={claim.provenance} data-testid="evidence-claim">
      {claim.text}
      <CitationChips citations={claim.citations} />
      <span className="ml-1 inline-flex flex-wrap items-center gap-1 align-middle">
        <span className="inline-flex items-center rounded-full border border-line-200 bg-surface-50 px-2 py-0.5 text-[11px] font-semibold text-ink-700" data-testid="evidence-provenance">
          {PROVENANCE_LABEL[claim.provenance]}
        </span>
        {claim.level !== "PROVISIONAL" ? <EvidenceLevelBadge level={claim.level} /> : null}
        {claim.sourcesDiffer ? <EvidenceSignalBadge signal="SOURCES_DIFFER" /> : null}
      </span>
    </p>
  );
}

function EvidenceEntryView({ entry }: { entry: EvidenceEntry }) {
  const [claim, ...folded] = usePageClaims([entry.claimId, ...entry.foldedIds]);
  return (
    <li className="min-w-0" data-testid="evidence-entry">
      <EvidenceClaim claim={claim} />
      {folded.length > 0 ? (
        <details className="mt-1.5">
          <summary className="w-fit cursor-pointer rounded-sm text-xs font-medium text-purple-700 hover:underline dark:text-purple-300">{countNoun(folded.length, "similar claim")}</summary>
          <ul className="mt-2 grid gap-2 border-l-2 border-line-200 pl-3" data-testid="evidence-folded">
            {folded.map((similar) => (
              <li key={similar.id}>
                <EvidenceClaim claim={similar} />
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </li>
  );
}

function EvidenceEntries({ entries }: { entries: readonly EvidenceEntry[] }) {
  return (
    <ul className="mt-2 grid gap-2.5">
      {entries.map((entry) => (
        <EvidenceEntryView key={entry.claimId} entry={entry} />
      ))}
    </ul>
  );
}

function SubjectView({ subject }: { subject: EvidenceSubject }) {
  return (
    <section className="min-w-0" data-testid="evidence-subject" data-kind={subject.subject.kind}>
      <h3 className="flex flex-wrap items-baseline gap-x-2 text-sm font-semibold text-ink-900">
        <span className="min-w-0 [overflow-wrap:anywhere]">{subject.subject.name}</span>
        <span className="text-xs font-medium text-ink-500">{SUBJECT_KIND_LABEL[subject.subject.kind]}</span>
      </h3>
      <EvidenceEntries entries={subject.entries} />
    </section>
  );
}

function GroupHeading({ id, title, count }: { id: string; title: string; count: number }) {
  return (
    <h2 id={id} className="flex flex-wrap items-baseline gap-x-2 font-display text-lg font-bold text-ink-900">
      {title}
      <span className="text-sm font-medium text-ink-500">{countNoun(count, "claim")}</span>
    </h2>
  );
}

export function CraftEvidence({ evidence }: { evidence: PageEvidence }) {
  return (
    <div className="grid gap-4" data-testid="craft-evidence">
      {evidence.groups.map((group) => (
        <section key={group.discipline} aria-labelledby={`evidence-${group.discipline}`} className="panel p-5 md:p-6" data-testid="evidence-group" data-discipline={group.discipline}>
          <GroupHeading id={`evidence-${group.discipline}`} title={group.title} count={groupCount(group)} />
          <div className="mt-4 grid gap-5">
            {group.subjects.map((subject) => (
              <SubjectView key={`${subject.subject.kind}:${subject.subject.id ?? subject.subject.name}`} subject={subject} />
            ))}
          </div>
        </section>
      ))}
      {evidence.hypotheses.length > 0 ? (
        <section aria-labelledby="evidence-hypotheses" className="panel p-5 md:p-6" data-testid="evidence-hypotheses">
          <GroupHeading id="evidence-hypotheses" title="Hypotheses" count={entryCount(evidence.hypotheses)} />
          <EvidenceEntries entries={evidence.hypotheses} />
        </section>
      ) : null}
    </div>
  );
}
