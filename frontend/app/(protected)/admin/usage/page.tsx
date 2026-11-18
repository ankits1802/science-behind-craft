"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { BarChart3, RotateCw } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { SegmentedChoice } from "@/components/ui/SegmentedChoice";
import { resolveRange, type RangeId } from "@/lib/dateRange";
import { formatDate } from "@/lib/format";
import { ceilingShare, fetchUsage, formatCount, formatUsd, money, monthlyCeiling, type UsageReport } from "@/lib/usage";

const PERIODS: { value: RangeId; label: string }[] = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "month", label: "This month" }
];

export default function UsagePage() {
  const [period, setPeriod] = useState<RangeId>("month");
  const [report, setReport] = useState<UsageReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [round, setRound] = useState(0);
  const generation = useRef(0);

  useEffect(() => {
    const mine = ++generation.current;
    fetchUsage(resolveRange({ range: period, from: "", to: "" }))
      .then((next) => {
        if (mine !== generation.current) return;
        setReport(next);
        setError(null);
      })
      .catch((err) => {
        if (mine !== generation.current) return;
        setError(err instanceof Error ? err.message : "Couldn't load usage.");
      });
  }, [period, round]);

  const share = report ? ceilingShare(report) : null;
  const busiestDay = useMemo(() => Math.max(0, ...(report?.byDay ?? []).map((row) => money(row.costUsd) ?? 0)), [report]);

  return (
    <>
      <PageHeader
        title="Usage"
        description="Model calls and spend."
        icon={<BarChart3 className="h-5 w-5" aria-hidden />}
        actions={<SegmentedChoice label="Period" value={period} options={PERIODS} onChange={(next) => setPeriod(next as RangeId)} />}
      />

      {error ? (
        <div role="alert" className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
          <button type="button" className="field-button-secondary min-h-8 px-3 py-1 text-xs" onClick={() => setRound((value) => value + 1)}>
            <RotateCw className="h-3.5 w-3.5" aria-hidden />
            Try again
          </button>
        </div>
      ) : null}

      {report === null ? (
        error ? null : <section className="panel p-6 text-sm text-ink-500">Loading…</section>
      ) : (
        <div className="grid gap-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <Stat label="Spend" value={formatUsd(report.spentUsd)} note={`${formatDate(report.from)} – ${formatDate(report.to)}`} />
            <Stat label="Calls" value={formatCount(report.calls)} note={report.failures > 0 ? `${formatCount(report.failures)} failed` : "None failed"} />
            {monthlyCeiling(report) === null ? (
              <Stat label="This month" value={formatUsd(report.spentThisMonthUsd)} note="No monthly ceiling" />
            ) : (
              <CeilingPanel report={report} share={share} />
            )}
          </div>

          <UsageTable
            title="By task"
            empty="No calls in this period."
            head={["Task", "Calls", "Failed", "Tokens in", "Tokens out", "Spend"]}
            rows={report.byTask.map((row) => [
              row.label,
              formatCount(row.calls),
              formatCount(row.failures),
              formatCount(row.inputTokens),
              formatCount(row.outputTokens),
              formatUsd(row.costUsd)
            ])}
          />

          <UsageTable
            title="By model"
            empty="No calls in this period."
            head={["Model", "Provider", "Calls", "Failed", "p95", "Spend"]}
            rows={report.byProvider.map((row) => [
              row.model,
              row.name,
              formatCount(row.calls),
              formatCount(row.failures),
              row.p95LatencyMs === null ? "—" : `${(row.p95LatencyMs / 1000).toFixed(1)} s`,
              formatUsd(row.costUsd)
            ])}
          />

          {report.byDay.length > 0 ? (
            <section className="panel p-5">
              <h2 className="font-display font-bold text-ink-900">By day</h2>
              <ol className="mt-3 grid gap-1.5">
                {report.byDay.map((row) => {
                  const cost = money(row.costUsd) ?? 0;
                  return (
                    <li key={row.day} className="grid grid-cols-[6.5rem_minmax(0,1fr)_5rem] items-center gap-3 text-xs">
                      <span className="tabular-nums text-ink-500">{formatDate(row.day)}</span>
                      <ProgressBar percent={busiestDay > 0 ? (cost / busiestDay) * 100 : 0} aria-hidden />
                      <span className="text-right tabular-nums text-ink-700">{formatUsd(row.costUsd)}</span>
                    </li>
                  );
                })}
              </ol>
            </section>
          ) : null}
        </div>
      )}
    </>
  );
}

function CeilingPanel({ report, share }: { report: UsageReport; share: number | null }) {
  return (
    <section className="panel p-5">
      <p className="field-label">Monthly ceiling</p>
      <p className="mt-2 font-display text-2xl font-bold tabular-nums text-ink-900">
        {formatUsd(report.spentThisMonthUsd)} <span className="text-sm font-medium text-ink-500">of {formatUsd(report.ceilingUsd)}</span>
      </p>
      {share !== null ? (
        <>
          <ProgressBar
            className="mt-3 h-2"
            percent={share}
            role="progressbar"
            aria-label="Monthly ceiling used"
            aria-valuenow={Math.round(share)}
            aria-valuemin={0}
            aria-valuemax={100}
          />
          <p className="mt-1.5 text-xs tabular-nums text-ink-500">{Math.round(share)}% used</p>
        </>
      ) : null}
    </section>
  );
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <section className="panel p-5">
      <p className="field-label">{label}</p>
      <p className="mt-2 font-display text-2xl font-bold tabular-nums text-ink-900">{value}</p>
      <p className="mt-1 text-xs text-ink-500">{note}</p>
    </section>
  );
}

function UsageTable({ title, head, rows, empty }: { title: string; head: string[]; rows: string[][]; empty: string }) {
  return (
    <section className="panel overflow-hidden">
      <h2 className="border-b border-line-200 px-4 py-3 font-display font-bold text-ink-900">{title}</h2>
      {rows.length === 0 ? (
        <p className="px-4 py-5 text-sm text-ink-500">{empty}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="bg-surface-50 text-xs uppercase tracking-wide text-ink-500">
              <tr>
                {head.map((cell, index) => (
                  <th key={cell} className={index === 0 ? "px-4 py-2.5" : "px-4 py-2.5 text-right"}>
                    {cell}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line-200">
              {rows.map((row, rowIndex) => (
                <tr key={`${row[0]}-${rowIndex}`}>
                  {row.map((cell, index) => (
                    <td key={index} className={index === 0 ? "px-4 py-2.5 font-medium text-ink-900" : "px-4 py-2.5 text-right tabular-nums text-ink-700"}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
