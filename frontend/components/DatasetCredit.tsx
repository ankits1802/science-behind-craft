import { safeOutboundUrl } from "@/lib/citations";
import type { RegionDataset } from "@/lib/regionContract";

const LINK = "underline-offset-2 hover:text-purple-700 hover:underline dark:hover:text-purple-300";

export function DatasetCredit({ dataset, methods = [] }: { dataset: RegionDataset; methods?: readonly string[] }) {
  const href = safeOutboundUrl(dataset.url);
  const licenceHref = safeOutboundUrl(dataset.licenceUrl);
  return (
    <span className="grid gap-0.5 text-[11px] leading-4 text-ink-500" data-testid="dataset-credit">
      <span>
        {href ? (
          <a href={href} target="_blank" rel="noopener noreferrer" className={`font-medium text-ink-700 ${LINK}`}>
            {dataset.title}
          </a>
        ) : (
          <span className="font-medium text-ink-700">{dataset.title}</span>
        )}
        {[dataset.publisher, dataset.edition].filter(Boolean).map((part) => ` · ${part}`)}
      </span>
      <span>
        {licenceHref ? (
          <a href={licenceHref} target="_blank" rel="noopener noreferrer" className={LINK}>
            {dataset.licence}
          </a>
        ) : (
          dataset.licence
        )}
        {dataset.attribution ? ` · ${dataset.attribution}` : null}
      </span>
      {dataset.citation ? <span>{dataset.citation}</span> : null}
      {methods.map((method) => (
        <span key={method}>Method: {method}</span>
      ))}
    </span>
  );
}
