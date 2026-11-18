"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode
} from "react";

import { FieldDialog, type DialogTone } from "@/components/dialogs/FieldDialog";
import { Button } from "@/components/ui/button";

export type ConfirmOptions = {
  title: string;
  body?: ReactNode;
  note?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: DialogTone;
};

export function ConfirmDialog({
  open,
  title,
  body,
  note,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "neutral",
  busy = false,
  onConfirm,
  onCancel
}: ConfirmOptions & {
  open: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement | null>(null);
  const confirmRef = useRef<HTMLButtonElement | null>(null);
  const destructive = tone === "danger";

  return (
    <FieldDialog
      open={open}
      onClose={onCancel}
      role={tone === "neutral" ? "dialog" : "alertdialog"}
      tone={tone}
      busy={busy}
      title={title}
      description={body}
      initialFocusRef={destructive ? cancelRef : confirmRef}
      footer={
        <>
          <Button ref={cancelRef} variant="quiet" disabled={busy} onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button ref={confirmRef} variant={destructive ? "destroy" : "primary"} data-danger={destructive ? "" : undefined} busy={busy} busyLabel="Working" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      {note ? <p className="mt-2 font-ui text-ui font-normal text-ink-3">{note}</p> : null}
    </FieldDialog>
  );
}

type ConfirmFn = (options: ConfirmOptions) => Promise<boolean>;

const ConfirmContext = createContext<ConfirmFn | undefined>(undefined);

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions>({ title: "" });
  const resolverRef = useRef<((value: boolean) => void) | null>(null);

  const settle = useCallback((value: boolean) => {
    const resolve = resolverRef.current;
    resolverRef.current = null;
    setOpen(false);
    resolve?.(value);
  }, []);

  const confirm = useCallback<ConfirmFn>(
    (next) =>
      new Promise<boolean>((resolve) => {
        resolverRef.current?.(false);
        resolverRef.current = resolve;
        setOptions(next);
        setOpen(true);
      }),
    []
  );

  useEffect(
    () => () => {
      resolverRef.current?.(false);
      resolverRef.current = null;
    },
    []
  );

  const value = useMemo(() => confirm, [confirm]);

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      <ConfirmDialog {...options} open={open} onConfirm={() => settle(true)} onCancel={() => settle(false)} />
    </ConfirmContext.Provider>
  );
}

export function useConfirm(): ConfirmFn {
  const context = useContext(ConfirmContext);
  if (!context) throw new Error("useConfirm must be used inside ConfirmProvider");
  return context;
}

export function useOptionalConfirm(): ConfirmFn | undefined {
  return useContext(ConfirmContext);
}

export function deleteConfirm(title: string, body?: ReactNode, note?: ReactNode): ConfirmOptions {
  return { title, body, note, tone: "danger", confirmLabel: "Delete" };
}
