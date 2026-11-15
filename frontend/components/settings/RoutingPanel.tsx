"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, CircleDashed, Loader2, Plus, RotateCw, ShieldQuestion, Trash2, XCircle } from "lucide-react";

import { FieldBlock } from "@/components/FormControls";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Dropdown } from "@/components/ui/Dropdown";
import { ToggleSwitch } from "@/components/ui/Toggle";
import { useToast } from "@/components/ui/Toast";
import { formatDateTime } from "@/lib/format";
import {
  fetchRouting,
  modelsForTask,
  moveRoute,
  routeKey,
  sameRoutes,
  saveTaskRoute,
  testTaskRoute,
  type KeyState,
  type RouteRow,
  type RoutingState,
  type TaskRoute
} from "@/lib/routing";
import { cn } from "@/lib/utils";

const KEY_BADGE: Record<KeyState, { label: string; className: string; Icon: typeof CheckCircle2 }> = {
  PASSING: { label: "Working", className: "text-success-600 dark:text-emerald-400", Icon: CheckCircle2 },
  FAILING: { label: "Test failed", className: "text-error-600", Icon: XCircle },
  UNTESTED: { label: "Not tested", className: "text-amber-800 dark:text-amber-500", Icon: ShieldQuestion },
  ABSENT: { label: "No key", className: "text-ink-500", Icon: CircleDashed }
};

export function RoutingPanel() {
  const { toast } = useToast();
  const [state, setState] = useState<RoutingState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [task, setTask] = useState("");
  const [draft, setDraft] = useState<RouteRow[]>([]);
  const [adding, setAdding] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const focusAfterMove = useRef<string | null>(null);
  const buttons = useRef(new Map<string, HTMLButtonElement | null>());

  const load = useCallback(() => {
    setLoading(true);
    fetchRouting()
      .then((next) => {
        setState(next);
        setLoadError(null);
        setTask((current) => (current && next.tasks.some((row) => row.task === current) ? current : (next.tasks[0]?.task ?? "")));
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Couldn't load the routing."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  const current = useMemo(() => state?.tasks.find((row) => row.task === task) ?? null, [state, task]);

  useEffect(() => {
    setDraft(current ? current.routes : []);
    setAdding("");
    setError(null);
  }, [current]);

  useEffect(() => {
    const key = focusAfterMove.current;
    if (!key) return;
    focusAfterMove.current = null;
    buttons.current.get(key)?.focus();
  }, [draft]);

  const providerName = useCallback(
    (id: string) => state?.providers.find((provider) => provider.id === id)?.name ?? id,
    [state]
  );

  const modelLabel = useCallback(
    (providerId: string, modelId: string) =>
      state?.providers.find((provider) => provider.id === providerId)?.models.find((model) => model.id === modelId)?.label ?? modelId,
    [state]
  );

  const candidates = useMemo(() => {
    if (!state || !current) return [];
    const taken = new Set(draft.map(routeKey));
    return modelsForTask(state.providers, current)
      .filter(({ provider, model }) => !taken.has(routeKey({ provider: provider.id, model: model.id })))
      .map(({ provider, model }) => ({ value: `${provider.id}:${model.id}`, label: model.label, hint: provider.name, group: provider.name }));
  }, [current, draft, state]);

  function applyTask(next: TaskRoute) {
    setState((prev) => (prev ? { ...prev, tasks: prev.tasks.map((row) => (row.task === next.task ? next : row)) } : prev));
  }

  function move(from: number, to: number) {
    if (to < 0 || to >= draft.length) return;
    const row = draft[from];
    setDraft((list) => moveRoute(list, from, to));
    setAnnouncement(`${modelLabel(row.provider, row.model)} moved to position ${to + 1} of ${draft.length}.`);
    const usable = to === 0 ? "down" : to === draft.length - 1 ? "up" : to > from ? "down" : "up";
    focusAfterMove.current = `${routeKey(row)}:${usable}`;
  }

  function add() {
    if (!adding || !state) return;
    const [provider, ...rest] = adding.split(":");
    const model = rest.join(":");
    const source = state.providers.find((row) => row.id === provider);
    if (!source) return;
    setDraft((list) => [...list, { provider: source.id, model, enabled: true, keyState: source.keyState, testedAt: null, testError: null }]);
    setAdding("");
    setAnnouncement(`${modelLabel(provider, model)} added at position ${draft.length + 1}.`);
  }

  async function save() {
    if (!current) return;
    setSaving(true);
    setError(null);
    try {
      const next = await saveTaskRoute(
        current.task,
        draft.map(({ provider, model, enabled }) => ({ provider, model, enabled }))
      );
      applyTask(next);
      toast({ title: next.normalisedNote ? "Saved with changes" : "Routing saved", description: next.normalisedNote ?? undefined, tone: next.normalisedNote ? "info" : "success" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save the routing.");
    } finally {
      setSaving(false);
    }
  }

  async function test(row: RouteRow) {
    if (!current) return;
    const key = routeKey(row);
    setTesting(key);
    setError(null);
    try {
      const next = await testTaskRoute(current.task, row.provider, row.model);
      const verdict = next.routes.find((candidate) => routeKey(candidate) === key);
      const merge = (list: RouteRow[]) =>
        list.map((item) =>
          routeKey(item) === key && verdict ? { ...item, keyState: verdict.keyState, testedAt: verdict.testedAt, testError: verdict.testError } : item
        );
      setDraft(merge);
      toast({
        title: verdict?.keyState === "PASSING" ? `${modelLabel(row.provider, row.model)} answered` : `${modelLabel(row.provider, row.model)} failed`,
        description: verdict?.keyState === "PASSING" ? undefined : (verdict?.testError ?? undefined),
        tone: verdict?.keyState === "PASSING" ? "success" : "error"
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't run the test.");
    } finally {
      setTesting(null);
    }
  }

  if (loading && !state) {
    return (
      <section className="panel flex items-center gap-2 p-5 text-sm text-ink-500">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        Loading…
      </section>
    );
  }

  if (!state) {
    return (
      <section className="panel grid justify-items-center gap-3 p-6 text-center" role="alert">
        <p className="text-sm text-ink-700">{loadError ?? "Couldn't load the routing."}</p>
        <button type="button" className="field-button" onClick={load}>
          <RotateCw className="h-4 w-4" aria-hidden />
          Try again
        </button>
      </section>
    );
  }

  const dirty = current ? !sameRoutes(draft, current.routes) : false;
  const taskOptions = state.tasks.map((row) => ({ value: row.task, label: row.label }));

  return (
    <section className="panel grid gap-4 p-5" data-testid="routing-panel">
      <div className="grid gap-3 sm:grid-cols-[minmax(0,18rem)_1fr] sm:items-end">
        <FieldBlock label="Task">
          <Dropdown value={task} onChange={setTask} options={taskOptions} searchable={false} advanceOnSelect={false} />
        </FieldBlock>
        {current && current.effectiveChain.length > 0 && !dirty ? (
          <p className="text-xs text-ink-500" data-testid="effective-chain">
            Now answering with <span className="font-medium text-ink-700">{current.effectiveChain.join(" → ")}</span>
          </p>
        ) : null}
      </div>

      {draft.length === 0 ? (
        <p className="flex items-start gap-2 rounded-md border border-amber-100 bg-amber-100/50 px-3 py-2.5 text-sm text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          Add at least one model.
        </p>
      ) : (
        <ol className="grid gap-2" data-testid="routing-list">
          {draft.map((row, index) => {
            const key = routeKey(row);
            const badge = KEY_BADGE[row.keyState];
            return (
              <li key={key} className={cn("flex flex-wrap items-start gap-3 rounded-md border border-line-200 bg-card px-3 py-3", !row.enabled && "opacity-70")}>
                <span
                  aria-hidden
                  className={cn(
                    "mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold",
                    row.enabled ? "bg-purple-700 text-white" : "bg-surface-50 text-ink-500 ring-1 ring-line-200"
                  )}
                >
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="text-sm font-semibold text-ink-900">{modelLabel(row.provider, row.model)}</span>
                    <span className="text-xs text-ink-500">{providerName(row.provider)}</span>
                    <span className={cn("inline-flex items-center gap-1 text-xs font-medium", badge.className)}>
                      <badge.Icon className="h-3.5 w-3.5" aria-hidden />
                      {badge.label}
                      {row.testedAt ? <span className="font-normal text-ink-500">· {formatDateTime(row.testedAt)}</span> : null}
                    </span>
                  </div>
                  {row.testError ? <p className="mt-1 text-xs leading-5 text-error-600">{row.testError}</p> : null}
                  <ToggleSwitch
                    className="mt-2"
                    label="Use this model"
                    showLabel
                    checked={row.enabled}
                    onChange={(next) => setDraft((list) => list.map((item) => (routeKey(item) === key ? { ...item, enabled: next } : item)))}
                  />
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  <button
                    type="button"
                    className="inline-flex min-h-8 items-center gap-1.5 rounded-sm border border-line-200 bg-card px-2.5 text-xs font-semibold text-ink-700 transition hover:border-purple-300 hover:bg-purple-50 hover:text-purple-700 disabled:opacity-40"
                    onClick={() => void test(row)}
                    disabled={testing !== null}
                    aria-label={`Test ${modelLabel(row.provider, row.model)}`}
                  >
                    {testing === key ? <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> : null}
                    {testing === key ? "Testing…" : "Test"}
                  </button>
                  <MoveButton
                    direction="up"
                    disabled={index === 0}
                    label={`Move ${modelLabel(row.provider, row.model)} up`}
                    register={(node) => buttons.current.set(`${key}:up`, node)}
                    onMove={() => move(index, index - 1)}
                  />
                  <MoveButton
                    direction="down"
                    disabled={index === draft.length - 1}
                    label={`Move ${modelLabel(row.provider, row.model)} down`}
                    register={(node) => buttons.current.set(`${key}:down`, node)}
                    onMove={() => move(index, index + 1)}
                  />
                  <button
                    type="button"
                    className="grid h-8 w-8 place-items-center rounded-sm border border-line-200 text-error-600 transition hover:bg-error-100"
                    aria-label={`Remove ${modelLabel(row.provider, row.model)}`}
                    onClick={() => setDraft((list) => list.filter((item) => routeKey(item) !== key))}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </button>
                </div>
              </li>
            );
          })}
        </ol>
      )}

      {candidates.length > 0 ? (
        <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
          <FieldBlock label="Add a model">
            <Dropdown value={adding} onChange={setAdding} options={candidates} placeholder="Choose a model" searchable advanceOnSelect={false} />
          </FieldBlock>
          <button type="button" className="field-button-secondary" disabled={!adding} onClick={add}>
            <Plus className="h-4 w-4" aria-hidden />
            Add
          </button>
        </div>
      ) : null}

      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>

      {error ? (
        <p role="alert" className="rounded-md border border-red-200 bg-error-100 px-3 py-2 text-sm text-error-600">
          {error}
        </p>
      ) : null}

      <ActionGroup align="start">
        <button type="button" className="field-button" disabled={!dirty || saving || draft.length === 0} onClick={() => void save()}>
          {saving ? "Saving…" : "Save order"}
        </button>
        {dirty ? (
          <button type="button" className="field-button-secondary" onClick={() => current && setDraft(current.routes)}>
            Reset
          </button>
        ) : null}
      </ActionGroup>
    </section>
  );
}

function MoveButton({
  direction,
  disabled,
  label,
  register,
  onMove
}: {
  direction: "up" | "down";
  disabled: boolean;
  label: string;
  register: (node: HTMLButtonElement | null) => void;
  onMove: () => void;
}) {
  const Icon = direction === "up" ? ChevronUp : ChevronDown;
  return (
    <button
      type="button"
      ref={register}
      className="grid h-8 w-8 place-items-center rounded-sm border border-line-200 text-ink-500 transition hover:border-purple-300 hover:bg-purple-50 hover:text-purple-700 disabled:cursor-not-allowed disabled:opacity-30"
      disabled={disabled}
      aria-label={label}
      onClick={onMove}
    >
      <Icon className="h-4 w-4" aria-hidden />
    </button>
  );
}
