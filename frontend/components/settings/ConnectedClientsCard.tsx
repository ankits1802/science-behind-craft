"use client";

import { useCallback, useEffect, useState } from "react";

import { useConfirm } from "@/components/dialogs/ConfirmDialog";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/Skeleton";
import { apiErrorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { scopeList } from "@/lib/oauthConsent";
import { fetchConnections, revokeConnection, type Connection, type ConnectionList } from "@/lib/oauthContract";

const LOAD_FAILED = "Couldn't load your connected apps.";
const REVOKE_FAILED = "Couldn't revoke the app. Try again.";

function ConnectedClientRow({ item, busy, onRevoke }: { item: Connection; busy: boolean; onRevoke: (item: Connection) => void }) {
  return (
    <li className="grid gap-1 border-t border-rule pt-3" data-testid="connected-app">
      <p className="text-ui font-ui font-semibold text-ink-1">
        {item.clientName} <span className="font-normal text-ink-3">· {item.clientHost}</span>
      </p>
      <p className="text-label font-ui text-ink-2">May {scopeList(item.scopes)}</p>
      <p className="text-label font-ui text-ink-3">
        Connected {formatDateTime(item.connectedAt)} · {item.lastUsedAt ? `last used ${formatDateTime(item.lastUsedAt)}` : "not used yet"}
      </p>
      <ActionGroup align="start">
        <Button type="button" variant="danger" size="sm" busy={busy} busyLabel="Revoking" onClick={() => onRevoke(item)} data-danger>
          Revoke
        </Button>
      </ActionGroup>
    </li>
  );
}

export function ConnectedClientsCard() {
  const confirm = useConfirm();
  const [list, setList] = useState<ConnectionList | null>(null);
  const [failed, setFailed] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setList(await fetchConnections());
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (list && !list.serverUrl && !list.connections.length) return null;

  async function revoke(item: Connection) {
    const sure = await confirm({
      title: `Revoke ${item.clientName}?`,
      body: "It can no longer use KalaVigyan in your name. Connect it again from the app if you need it.",
      tone: "danger",
      confirmLabel: "Revoke"
    });
    if (!sure) return;
    setBusyId(item.id);
    setError(null);
    try {
      await revokeConnection(item.id);
      await load();
    } catch (cause) {
      setError(apiErrorMessage(cause, REVOKE_FAILED));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="flex h-full flex-col gap-3 rounded-card border border-rule bg-raised p-5" aria-labelledby="connected-apps-h" data-testid="connected-apps">
      <h2 id="connected-apps-h" className="text-h4 font-ui text-ink-1">
        Connected apps
      </h2>
      {!list && !failed ? <Skeleton shape="lede" label="Fetching your connected apps" /> : null}
      {failed ? (
        <div role="alert" className="grid justify-items-start gap-2">
          <p className="text-ui font-ui text-error">{LOAD_FAILED}</p>
          <Button type="button" variant="quiet" size="sm" onClick={() => void load()}>
            Try again
          </Button>
        </div>
      ) : null}
      {list && !list.connections.length ? (
        <p className="text-body-sm font-reading text-ink-2">
          Apps you connect to KalaVigyan appear here with what each may do. To connect one, add <span className="font-code break-all">{list.serverUrl}</span> as an MCP server in the app.
        </p>
      ) : null}
      {list?.connections.length ? (
        <ul className="grid gap-3">
          {list.connections.map((item) => (
            <ConnectedClientRow key={item.id} item={item} busy={busyId === item.id} onRevoke={(next) => void revoke(next)} />
          ))}
        </ul>
      ) : null}
      {error ? <p role="alert" className="text-ui font-ui text-error">{error}</p> : null}
    </section>
  );
}
