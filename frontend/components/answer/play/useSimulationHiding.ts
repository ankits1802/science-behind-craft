"use client";

import { useCallback, useState } from "react";

import { setSimulationHidden } from "@/lib/simulationView";

export type HidingControls = { hidden: boolean; busy: boolean; failed: boolean; change: (hidden: boolean) => void };

export function useSimulationHiding(answerId: string | null, blockId: string, storedHidden: boolean): HidingControls | null {
  const [hidden, setHidden] = useState(storedHidden);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const change = useCallback(
    (next: boolean) => {
      if (answerId === null || busy) return;
      setBusy(true);
      setFailed(false);
      setSimulationHidden(answerId, blockId, next)
        .then((answer) => setHidden(answer.hidden))
        .catch((cause: unknown) => {
          console.error(cause);
          setFailed(true);
        })
        .finally(() => setBusy(false));
    },
    [answerId, blockId, busy]
  );
  return answerId === null ? null : { hidden, busy, failed, change };
}
