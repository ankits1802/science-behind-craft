import { openCredit, openReadNote, type OpenSource } from "@/lib/imageContributionContract";

type Detail = "credit" | "evidence";

function NewTab({ href, children }: { href: string; children: string }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="kv-link font-normal">
      {children}
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}

export function OpenPictureEvidence({ source, detail }: { source: OpenSource; detail: Detail }) {
  const credit = openCredit(source);
  return (
    <div className="grid gap-1" data-testid="open-picture-evidence">
      <p className="text-caption font-ui text-ink-3">
        {credit.prefix}
        <NewTab href={source.pageUrl}>{credit.linked}</NewTab>
      </p>
      {detail === "evidence" ? (
        <>
          <p className="text-label font-ui text-ink-2">
            Licence: {source.licenceUrl ? <NewTab href={source.licenceUrl}>{source.licence}</NewTab> : source.licence} · {source.title}
          </p>
          <p className="text-label font-ui text-ink-2">
            <NewTab href={source.recordUrl}>{openReadNote(source)}</NewTab>
          </p>
        </>
      ) : null}
    </div>
  );
}
