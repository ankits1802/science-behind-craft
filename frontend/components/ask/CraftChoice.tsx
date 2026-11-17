"use client";

import { motion } from "framer-motion";

import { slideItem, staggerParent } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { ANY_CRAFT, craftPickOf, craftValue, type CraftOffer, type CraftOption, type CraftPick } from "@/lib/askCraft";

const CANDIDATE_CLASS =
  "inline-flex min-h-9 items-center rounded-full border border-line-200 bg-card px-3.5 text-xs font-semibold text-ink-900 transition hover:border-purple-300 hover:bg-purple-50 dark:hover:bg-purple-950/40 pointer-coarse:min-h-11";

export function CraftChoice({
  pick,
  options,
  offer,
  onPick
}: {
  pick: CraftPick;
  options: CraftOption[];
  offer: CraftOffer;
  onPick: (pick: CraftPick) => void;
}) {
  const reduce = useAppReducedMotion();
  const candidates = offer.candidates;
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-2" data-testid="craft-choice">
      <SearchableSelect
        value={craftValue(pick, offer)}
        options={options}
        noneLabel={offer.noneLabel}
        placeholder={ANY_CRAFT}
        onChange={(next) => onPick(craftPickOf(next))}
        ariaLabel="Craft"
        searchable
        advanceOnSelect={false}
        className="w-full sm:w-64"
      />
      {candidates.length > 0 ? (
        <motion.div key={candidates.map((craft) => craft.slug).join(" ")} variants={staggerParent(reduce, 0.05)} initial="hidden" animate="show" className="flex min-w-0 flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-ink-500">Or</span>
          <ActionGroup inline align="start">
            {candidates.map((craft) => (
              <motion.button key={craft.slug} type="button" variants={slideItem(reduce)} onClick={() => onPick({ craftSlug: craft.slug, anyCraft: false })} className={CANDIDATE_CLASS}>
                {craft.name}
              </motion.button>
            ))}
          </ActionGroup>
        </motion.div>
      ) : null}
    </div>
  );
}
