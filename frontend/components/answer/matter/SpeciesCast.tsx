"use client";

import { Circle, Diamond, type LucideIcon } from "lucide-react";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { CAST_ROLE_LABEL, type CastMember, type CastRole } from "@/lib/reactionPlayer";
import { cn } from "@/lib/utils";

const ROLE_TONE: Record<CastRole, string> = {
  REACTANT: "border-purple-600 bg-purple-100 text-ink-900 dark:border-purple-400 dark:bg-purple-950/70",
  PRODUCT: "border-archive-600 bg-archive-100 text-ink-900 dark:border-archive-400 dark:bg-archive-950/70"
};

const ROLE_MARK: Record<CastRole, { Icon: LucideIcon; className: string }> = {
  REACTANT: { Icon: Circle, className: "fill-purple-600 text-purple-600 dark:fill-purple-300 dark:text-purple-300" },
  PRODUCT: { Icon: Diamond, className: "fill-archive-600 text-archive-600 dark:fill-archive-300 dark:text-archive-300" }
};

const RESTING = "border-line-200 bg-card text-ink-500";

function RoleMark({ role }: { role: CastRole }) {
  const { Icon, className } = ROLE_MARK[role];
  return <Icon className={cn("h-2.5 w-2.5 shrink-0", className)} aria-hidden />;
}

function CastChip({ member, role }: { member: CastMember; role: CastRole | null }) {
  return (
    <li
      title={member.name}
      data-testid="cast-species"
      data-role={role ?? "none"}
      className={cn("inline-flex min-h-8 max-w-full items-center gap-1.5 rounded-full border px-2.5 text-sm transition-colors duration-300", role ? ROLE_TONE[role] : RESTING)}
    >
      {role ? <RoleMark role={role} /> : null}
      {member.formula ? (
        <ChemEquation equation={member.formula} display={false} label={member.name} />
      ) : (
        <span className="min-w-0 break-words text-xs font-semibold">{member.name}</span>
      )}
      {role ? <span className="sr-only">{`, ${CAST_ROLE_LABEL[role]}`}</span> : null}
    </li>
  );
}

export function SpeciesCast({ cast, roles }: { cast: readonly CastMember[]; roles: ReadonlyMap<string, CastRole> }) {
  return (
    <div className="min-w-0 rounded-lg border border-line-200 bg-surface-50 p-3" data-testid="species-cast">
      <ul className="flex min-w-0 flex-wrap gap-1.5" aria-label="Species in this reaction">
        {cast.map((member) => (
          <CastChip key={member.key} member={member} role={roles.get(member.key) ?? null} />
        ))}
      </ul>
      <p aria-hidden className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-500">
        {(["REACTANT", "PRODUCT"] as const).map((role) => (
          <span key={role} className="inline-flex items-center gap-1.5">
            <RoleMark role={role} />
            {`${CAST_ROLE_LABEL[role]}s`}
          </span>
        ))}
      </p>
    </div>
  );
}
