export const RANGE_IDS = ["any", "today", "7d", "30d", "90d", "month", "year", "custom"] as const;
export type RangeId = (typeof RANGE_IDS)[number];

function startOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function endOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999);
}

function daysBefore(date: Date, days: number) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() - days);
}

function parseDateInput(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
  if (!match) return null;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return Number.isNaN(date.getTime()) ? null : date;
}

export function resolveRange(
  filters: { range: RangeId; from: string; to: string },
  now: Date = new Date()
): { dateFrom?: string; dateTo?: string } {
  const untilNow = { dateTo: endOfDay(now).toISOString() };
  switch (filters.range) {
    case "today":
      return { dateFrom: startOfDay(now).toISOString(), ...untilNow };
    case "7d":
      return { dateFrom: daysBefore(now, 6).toISOString(), ...untilNow };
    case "30d":
      return { dateFrom: daysBefore(now, 29).toISOString(), ...untilNow };
    case "90d":
      return { dateFrom: daysBefore(now, 89).toISOString(), ...untilNow };
    case "month":
      return { dateFrom: new Date(now.getFullYear(), now.getMonth(), 1).toISOString(), ...untilNow };
    case "year":
      return { dateFrom: new Date(now.getFullYear(), 0, 1).toISOString(), ...untilNow };
    case "custom": {
      const from = parseDateInput(filters.from);
      const to = parseDateInput(filters.to);
      return {
        dateFrom: from ? startOfDay(from).toISOString() : undefined,
        dateTo: to ? endOfDay(to).toISOString() : undefined
      };
    }
    default:
      return {};
  }
}
