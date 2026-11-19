"use client";

import { useState } from "react";

import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { TextLink } from "@/components/ui/TextLink";
import { apiErrorMessage } from "@/lib/api";
import { closedLinkLine, closedLinkTitle, PICTURES_PATH, renewUploadLink, type UploadLinkView } from "@/lib/uploadLinkContract";

export function ClosedUploadLink({ token, view, onRenewed }: { token: string; view: UploadLinkView; onRenewed: (token: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  async function renew() {
    setBusy(true);
    setProblem(null);
    try {
      onRenewed((await renewUploadLink(token)).token);
    } catch (cause) {
      setProblem(apiErrorMessage(cause, "Couldn't make a new link. Try again."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="grid gap-4 border-t border-ink-1 pt-4" aria-labelledby="closed-link-h" data-testid="closed-upload-link">
      <h2 id="closed-link-h" className="text-h3 font-reading text-ink-1">
        {closedLinkTitle(view)}
      </h2>
      <p className="text-body-sm font-reading text-ink-2">{closedLinkLine(view)}</p>
      {problem ? (
        <p role="alert" className="text-ui font-ui text-error">
          {problem}
        </p>
      ) : null}
      <ActionGroup align="start">
        <Button type="button" busy={busy} busyLabel="Making a new link" onClick={() => void renew()}>
          Get a new link
        </Button>
      </ActionGroup>
      {view.state === "USED" ? (
        <TextLink href={PICTURES_PATH} standalone>
          See your pictures
        </TextLink>
      ) : null}
    </section>
  );
}
