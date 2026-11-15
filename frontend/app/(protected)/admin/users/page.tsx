"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { UserCog } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { useConfirm } from "@/components/dialogs/ConfirmDialog";
import { FieldDialog } from "@/components/dialogs/FieldDialog";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { ResizableTh } from "@/components/ResizableTh";
import { RowActions, rowAction } from "@/components/RowActions";
import { SearchInput } from "@/components/SearchInput";
import { RecordDetailsDialog } from "@/components/records/RecordDetailsDialog";
import { OpenableRow } from "@/components/data/OpenableRow";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Dropdown } from "@/components/ui/Dropdown";
import { FieldBlock } from "@/components/FormControls";
import { useToast } from "@/components/ui/Toast";
import { formatDateTime } from "@/lib/format";
import { ROLES_BY_RANK, roleLabel } from "@/lib/permissions";
import { resetTwoFactorForUser } from "@/lib/twoFactor";
import type { PageResult, User, UserRole } from "@/lib/types";

import {
  STANDING_LABEL,
  accountStanding,
  changeUserRole,
  listUsers,
  reactivateUser,
  roleChoices,
  rowOffers,
  suspendUser,
  twoStepFact
} from "./userAdmin";

const SEARCH_DELAY_MS = 300;

export default function ManageUsersPage() {
  return (
    <Suspense fallback={<Header />}>
      <ManageUsers />
    </Suspense>
  );
}

function Header() {
  return <PageHeader title="Manage users" description="Roles and access for every account." icon={<UserCog className="h-5 w-5" aria-hidden />} />;
}

function ManageUsers() {
  const { user: viewer } = useAuth();
  const confirm = useConfirm();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PageResult<User> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [roleFor, setRoleFor] = useState<User | null>(null);
  const [viewing, setViewing] = useState<User | null>(null);
  const generation = useRef(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search.trim());
      setPage(1);
    }, SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [search]);

  const load = useCallback(async () => {
    const mine = ++generation.current;
    try {
      const next = await listUsers({ search: query || undefined, role: role || undefined, page });
      if (mine !== generation.current) return;
      setData(next);
      setError(null);
    } catch (err) {
      if (mine !== generation.current) return;
      setError(err instanceof Error ? err.message : "Couldn't load accounts.");
    }
  }, [page, query, role]);

  useEffect(() => {
    void load();
  }, [load]);

  function replaceRow(next: User) {
    setData((current) =>
      current ? { ...current, items: current.items.map((item) => (item.id === next.id ? { ...item, ...next } : item)) } : current
    );
  }

  async function run(target: User, action: () => Promise<User>, done: string) {
    setBusyId(target.id);
    try {
      replaceRow(await action());
      toast({ title: done, tone: "success" });
    } catch (err) {
      toast({ title: err instanceof Error ? err.message : "That didn't work. Try again.", tone: "error" });
    } finally {
      setBusyId(null);
    }
  }

  async function suspend(target: User) {
    const ok = await confirm({
      title: `Suspend ${target.name || target.email}?`,
      body: "They are signed out and can't sign in until reactivated.",
      confirmLabel: "Suspend",
      tone: "danger"
    });
    if (ok) await run(target, () => suspendUser(target.id), "Account suspended.");
  }

  async function reactivate(target: User) {
    await run(target, () => reactivateUser(target.id), "Account reactivated.");
  }

  async function resetTwoStep(target: User) {
    const ok = await confirm({
      title: `Reset two-step verification for ${target.name || target.email}?`,
      body: "They set it up again at their next sign-in.",
      confirmLabel: "Reset",
      tone: "warning"
    });
    if (ok) await run(target, () => resetTwoFactorForUser(target.id), "Two-step verification reset.");
  }

  const roleOptions = [{ value: "", label: "Every role" }, ...ROLES_BY_RANK.map((value) => ({ value, label: roleLabel(value) }))];

  return (
    <>
      <Header />

      <section className="panel mb-4 grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_14rem]">
        <SearchInput value={search} onChange={setSearch} placeholder="Search by name or email" ariaLabel="Search accounts" />
        <Dropdown
          value={role}
          onChange={(next) => {
            setRole(next);
            setPage(1);
          }}
          options={roleOptions}
          ariaLabel="Role"
          searchable={false}
          advanceOnSelect={false}
        />
      </section>

      {error ? (
        <div role="alert" className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <section className="panel overflow-hidden">
        {data === null ? (
          <p className="p-6 text-sm text-ink-500">Loading…</p>
        ) : data.items.length === 0 ? (
          <div className="p-4">
            <EmptyState title={query || role ? "No account matches." : "No accounts yet."} />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="bg-surface-50 text-xs uppercase tracking-wide text-ink-500">
                  <tr>
                    <ResizableTh>Account</ResizableTh>
                    <ResizableTh>Role</ResizableTh>
                    <ResizableTh>Two-step</ResizableTh>
                    <ResizableTh>Last sign-in</ResizableTh>
                    <ResizableTh>Status</ResizableTh>
                    <th className="px-4 py-3 text-right">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line-200">
                  {data.items.map((account) => {
                    const offers = rowOffers(viewer, account);
                    const standing = accountStanding(account);
                    const busy = busyId === account.id;
                    return (
                      <OpenableRow key={account.id} onOpen={() => setViewing(account)}>
                        <td className="px-4 py-3">
                          <button type="button" onClick={() => setViewing(account)} className="text-left">
                            <span className="block font-medium text-ink-900">{account.name || account.email}</span>
                            <span className="block text-xs text-ink-500">{account.email}</span>
                          </button>
                        </td>
                        <td className="px-4 py-3 text-ink-700">{roleLabel(account.role)}</td>
                        <td className="px-4 py-3 text-ink-700">{twoStepFact(account)}</td>
                        <td className="px-4 py-3 text-ink-700">{account.lastLoginAt ? formatDateTime(account.lastLoginAt) : "Never"}</td>
                        <td className="px-4 py-3">
                          <span
                            className={
                              standing === "SUSPENDED"
                                ? "inline-flex rounded-full bg-error-100 px-2 py-0.5 text-xs font-semibold text-error-600"
                                : "inline-flex rounded-full bg-success-100 px-2 py-0.5 text-xs font-semibold text-success-600"
                            }
                          >
                            {STANDING_LABEL[standing]}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <RowActions>
                            {offers.role ? (
                              <button type="button" className={rowAction("edit")} disabled={busy} onClick={() => setRoleFor(account)}>
                                Change role
                              </button>
                            ) : null}
                            {offers.resetTwoStep ? (
                              <button type="button" className={rowAction("neutral")} disabled={busy} onClick={() => void resetTwoStep(account)}>
                                Reset two-step
                              </button>
                            ) : null}
                            {offers.reactivate ? (
                              <button type="button" className={rowAction("positive")} disabled={busy} onClick={() => void reactivate(account)}>
                                Reactivate
                              </button>
                            ) : null}
                            {offers.suspend ? (
                              <button type="button" data-danger className={rowAction("danger")} disabled={busy} onClick={() => void suspend(account)}>
                                Suspend
                              </button>
                            ) : null}
                          </RowActions>
                        </td>
                      </OpenableRow>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} />
          </>
        )}
      </section>

      {roleFor ? (
        <RoleDialog
          viewer={viewer}
          target={roleFor}
          onClose={() => setRoleFor(null)}
          onSaved={(next) => {
            replaceRow(next);
            setRoleFor(null);
            toast({ title: `${next.name || next.email} is now ${roleLabel(next.role)}.`, tone: "success" });
          }}
        />
      ) : null}

      <RecordDetailsDialog
        open={viewing !== null}
        onClose={() => setViewing(null)}
        title={viewing?.name || viewing?.email || ""}
        details={
          viewing
            ? [
                ["Email", viewing.email],
                ["Role", roleLabel(viewing.role)],
                ["Affiliation", viewing.affiliation ?? null],
                ["Two-step verification", twoStepFact(viewing)],
                ["Status", STANDING_LABEL[accountStanding(viewing)]],
                ["First sign-in", viewing.firstLoginAt ? formatDateTime(viewing.firstLoginAt) : null],
                ["Last sign-in", viewing.lastLoginAt ? formatDateTime(viewing.lastLoginAt) : null]
              ]
            : []
        }
      />
    </>
  );
}

function RoleDialog({
  viewer,
  target,
  onClose,
  onSaved
}: {
  viewer: User | null;
  target: User;
  onClose: () => void;
  onSaved: (next: User) => void;
}) {
  const [role, setRole] = useState<UserRole>(target.role);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const options = roleChoices(viewer, target).map((value) => ({ value, label: roleLabel(value) }));

  async function save() {
    setSaving(true);
    setError(null);
    try {
      onSaved(await changeUserRole(target.id, role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't change the role.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <FieldDialog
      open
      onClose={onClose}
      title={`Role for ${target.name || target.email}`}
      busy={saving}
      footer={
        <ActionGroup align="end">
          <button type="button" className="field-button-secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="button" className="field-button" onClick={() => void save()} disabled={saving || role === target.role}>
            {saving ? "Saving…" : "Save role"}
          </button>
        </ActionGroup>
      }
    >
      <FieldBlock label="Role">
        <Dropdown value={role} onChange={(next) => setRole(next as UserRole)} options={options} searchable={false} advanceOnSelect={false} />
      </FieldBlock>
      {error ? (
        <p role="alert" className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </FieldDialog>
  );
}
