import { apiFetch, buildQuery } from "@/lib/api";

export type Money = string | number | null;

export type UsageTaskRow = {
  task: string;
  label: string;
  calls: number;
  failures: number;
  inputTokens: number;
  outputTokens: number;
  costUsd: Money;
};

export type UsageProviderRow = {
  provider: string;
  name: string;
  model: string;
  calls: number;
  failures: number;
  costUsd: Money;
  p95LatencyMs: number | null;
};

export type UsageDayRow = { day: string; calls: number; costUsd: Money };

export type UsageReport = {
  from: string;
  to: string;
  ceilingUsd: Money;
  spentThisMonthUsd: Money;
  spentUsd: Money;
  calls: number;
  failures: number;
  byTask: UsageTaskRow[];
  byProvider: UsageProviderRow[];
  byDay: UsageDayRow[];
};

export function fetchUsage(range: { dateFrom?: string; dateTo?: string }): Promise<UsageReport> {
  return apiFetch<UsageReport>(`/usage/report${buildQuery({ from: range.dateFrom, to: range.dateTo })}`);
}

export function money(value: Money): number | null {
  if (value === null || value === undefined) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function formatUsd(value: Money): string {
  const number = money(value);
  if (number === null) return "—";
  return `$${number.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: number < 1 ? 4 : 2 })}`;
}

export function formatCount(value: number | null | undefined): string {
  return Number.isFinite(value) ? (value as number).toLocaleString("en-IN") : "—";
}

export function ceilingShare(report: UsageReport): number | null {
  const ceiling = money(report.ceilingUsd);
  const spent = money(report.spentThisMonthUsd);
  if (ceiling === null || spent === null || ceiling <= 0) return null;
  return (spent / ceiling) * 100;
}
