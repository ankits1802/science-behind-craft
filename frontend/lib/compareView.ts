import type { CompareRow } from "@/lib/explainerLearning";
import { DISCIPLINE_LABEL } from "@/lib/explainerView";

export type CompareLayout = { row: string; head: string; cell: string; cellName: string };
export type RowTitle = { title: string; facet: string | null };

const STACKED_ROW = "grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2 rounded-md border border-line-200 p-3";
const STACKED_CELL = "grid min-w-0 content-start gap-1 rounded-md bg-surface-50 p-3";

const SIDE_BY_SIDE: Record<number, CompareLayout> = {
  2: {
    row: `${STACKED_ROW} sm:grid-cols-[minmax(0,8rem)_repeat(2,minmax(0,1fr))] sm:gap-4 sm:rounded-none sm:border-x-0 sm:border-b-0 sm:px-0 sm:pb-0 sm:pt-3`,
    head: "max-sm:sr-only sm:grid sm:grid-cols-[minmax(0,8rem)_repeat(2,minmax(0,1fr))] sm:gap-4",
    cell: `${STACKED_CELL} sm:bg-transparent sm:p-0`,
    cellName: "sm:sr-only"
  },
  3: {
    row: `${STACKED_ROW} md:grid-cols-[minmax(0,8rem)_repeat(3,minmax(0,1fr))] md:gap-4 md:rounded-none md:border-x-0 md:border-b-0 md:px-0 md:pb-0 md:pt-3`,
    head: "max-md:sr-only md:grid md:grid-cols-[minmax(0,8rem)_repeat(3,minmax(0,1fr))] md:gap-4",
    cell: `${STACKED_CELL} md:bg-transparent md:p-0`,
    cellName: "md:sr-only"
  },
  4: {
    row: `${STACKED_ROW} lg:grid-cols-[minmax(0,8rem)_repeat(4,minmax(0,1fr))] lg:gap-4 lg:rounded-none lg:border-x-0 lg:border-b-0 lg:px-0 lg:pb-0 lg:pt-3`,
    head: "max-lg:sr-only lg:grid lg:grid-cols-[minmax(0,8rem)_repeat(4,minmax(0,1fr))] lg:gap-4",
    cell: `${STACKED_CELL} lg:bg-transparent lg:p-0`,
    cellName: "lg:sr-only"
  }
};

export function compareLayout(craftCount: number): CompareLayout {
  const layout = SIDE_BY_SIDE[craftCount];
  if (!layout) throw new RangeError(`a comparison sets 2 to 4 crafts side by side, not ${craftCount}`);
  return layout;
}

export function rowTitle(row: CompareRow): RowTitle {
  const facet = DISCIPLINE_LABEL[row.facet];
  return row.term ? { title: row.term.label, facet } : { title: facet, facet: null };
}
