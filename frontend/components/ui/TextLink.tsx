import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type Shared = { children: ReactNode; standalone?: boolean; className?: string };

type AsLink = Shared & { href: string; external?: boolean };

type AsButton = Shared & { onClick: () => void; expanded?: boolean; controls?: string; describedBy?: string };

export function TextLink(props: AsLink | AsButton) {
  const className = cn("kv-link", props.className);
  const standalone = props.standalone ? "" : undefined;
  if ("href" in props) {
    if (props.external) {
      return (
        <a href={props.href} className={className} data-standalone={standalone} target="_blank" rel="noopener noreferrer">
          {props.children}
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
      );
    }
    return (
      <Link href={props.href} className={className} data-standalone={standalone}>
        {props.children}
      </Link>
    );
  }
  return (
    <button type="button" onClick={props.onClick} className={className} data-standalone={standalone} aria-expanded={props.expanded} aria-controls={props.controls} aria-describedby={props.describedBy}>
      {props.children}
    </button>
  );
}
