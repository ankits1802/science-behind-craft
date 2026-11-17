"use client";

import Link from "next/link";
import { motion } from "framer-motion";

import { riseItem, staggerParent } from "@/components/guide/guideMotion";
import type { CraftLink } from "@/lib/answerShapes";
import { graphLayout, graphSummary, type GraphPoint } from "@/lib/conceptGraph";
import type { ConceptNode } from "@/lib/explainerLearning";
import { cn } from "@/lib/utils";

const CHIP_SHAPE = "inline-flex max-w-full items-center justify-center rounded-full border text-center font-semibold leading-tight shadow-sm";
const CHIP = `${CHIP_SHAPE} px-2.5 py-1 text-[11px] sm:text-xs`;
const CROWDED = 5;

function placed(at: GraphPoint) {
  return { left: `${at.x}%`, top: `${at.y}%` };
}

function Spokes({ points, reduce }: { points: GraphPoint[]; reduce: boolean }) {
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full" aria-hidden>
      {points.map((point, index) => (
        <motion.line
          key={`${point.x}-${point.y}`}
          x1={50}
          y1={50}
          x2={point.x}
          y2={point.y}
          vectorEffect="non-scaling-stroke"
          strokeWidth={1.5}
          className="stroke-purple-300 dark:stroke-purple-700"
          initial={reduce ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: reduce ? 0 : 0.4, delay: reduce ? 0 : 0.05 * index }}
          data-testid="concept-spoke"
        />
      ))}
    </svg>
  );
}

export function ConceptGraphFigure({ node, focus, reduce }: { node: ConceptNode; focus: CraftLink | null; reduce: boolean }) {
  const layout = graphLayout(node, focus);
  const points = [...layout.crafts.map((craft) => craft.at), ...(layout.more ? [layout.more.at] : [])];
  return (
    <figure className="m-0 min-w-0" data-testid="concept-figure">
      <div role="img" aria-label={graphSummary(node)} className={cn("relative w-full min-w-0 overflow-hidden rounded-lg border border-line-200 bg-surface-50 sm:aspect-[5/2]", points.length > CROWDED ? "aspect-square" : "aspect-[4/3]")}>
        <Spokes points={points} reduce={reduce} />
        <motion.div key={node.termKey} aria-hidden className="absolute inset-0" variants={staggerParent(reduce, 0.04)} initial={reduce ? false : "hidden"} animate="show">
          <span className="absolute flex w-[34%] -translate-x-1/2 -translate-y-1/2 justify-center" style={placed({ x: 50, y: 50 })}>
            <motion.span variants={riseItem(reduce, 6)} className={cn(CHIP_SHAPE, "border-purple-700 bg-purple-700 px-3 py-1.5 font-display text-sm text-white")} data-testid="concept-hub">
              {node.label}
            </motion.span>
          </span>
          {layout.crafts.map((craft) => (
            <span key={craft.entry.craft.slug} className="absolute flex w-[28%] -translate-x-1/2 -translate-y-1/2 justify-center" style={placed(craft.at)}>
              <motion.span variants={riseItem(reduce, 6)} className="flex max-w-full justify-center">
                <Link
                  href={craft.entry.craft.path}
                  tabIndex={-1}
                  className={cn(
                    CHIP,
                    craft.focus
                      ? "border-purple-700 bg-purple-50 text-purple-800 dark:border-purple-300 dark:bg-purple-950 dark:text-purple-100"
                      : "border-line-200 bg-card text-ink-900 hover:border-purple-300"
                  )}
                  data-testid="concept-craft-node"
                  data-focus={craft.focus ? "true" : "false"}
                >
                  {craft.entry.craft.name}
                </Link>
              </motion.span>
            </span>
          ))}
          {layout.more ? (
            <span className="absolute flex w-[28%] -translate-x-1/2 -translate-y-1/2 justify-center" style={placed(layout.more.at)}>
              <motion.span variants={riseItem(reduce, 6)} className={cn(CHIP, "border-dashed border-line-200 bg-card text-ink-500")} data-testid="concept-more">
                +{layout.more.count}
              </motion.span>
            </span>
          ) : null}
        </motion.div>
      </div>
    </figure>
  );
}
