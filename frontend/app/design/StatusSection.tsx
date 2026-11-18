"use client";

import { useState } from "react";

import { Demo, Grid, Section } from "@/app/design/DesignParts";
import { ConfirmDialog } from "@/components/dialogs/ConfirmDialog";
import { FieldDialog } from "@/components/dialogs/FieldDialog";
import { TypographicPlate } from "@/components/editorial/TypographicPlate";
import { EmptyState } from "@/components/EmptyState";
import { Field, TextInput } from "@/components/FormControls";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { Sheet } from "@/components/ui/Sheet";
import { Skeleton } from "@/components/ui/Skeleton";
import { ToastCard, useToast, type ToastRecord } from "@/components/ui/Toast";

const TOASTS: ToastRecord[] = [
  { id: "demo-success", tone: "success", title: "Saved to your list", description: "How does indigo turn blue on Kutch Ajrakh cloth?", duration: 0 },
  { id: "demo-info", tone: "info", title: "Citation copied", duration: 0 },
  { id: "demo-warning", tone: "warning", title: "Your session ends in 5 minutes", description: "Save your notes to keep them.", duration: 0 },
  { id: "demo-error", tone: "error", title: "The answer could not be saved", description: "Check your connection and try again.", duration: 0 }
];

function Overlays() {
  const { toast } = useToast();
  const [confirm, setConfirm] = useState(false);
  const [request, setRequest] = useState(false);
  const [sheet, setSheet] = useState(false);
  return (
    <>
      <ActionGroup align="start">
        <Button variant="quiet" size="sm" onClick={() => toast({ title: "Citation copied", tone: "success" })}>Show a toast</Button>
        <Button variant="quiet" size="sm" onClick={() => setConfirm(true)}>Open a destructive dialog</Button>
        <Button variant="quiet" size="sm" onClick={() => setRequest(true)}>Open a form dialog</Button>
        <Button variant="quiet" size="sm" onClick={() => setSheet(true)}>Open a sheet</Button>
      </ActionGroup>
      <ConfirmDialog open={confirm} tone="danger" title="Delete this lesson?" body="The slides and notes go for good. The answers it used stay in your saved list." confirmLabel="Delete lesson" cancelLabel="Keep it" onConfirm={() => setConfirm(false)} onCancel={() => setConfirm(false)} />
      <FieldDialog open={request} onClose={() => setRequest(false)} title="Request access" description="KalaVigyan opens to IIT professors, researchers and design students. We reply within two working days." footer={<Button variant="primary" onClick={() => setRequest(false)}>Send request</Button>}>
        <div className="mt-4">
          <Field label="Institution email">
            <TextInput placeholder="name@iitkgp.ac.in" />
          </Field>
        </div>
      </FieldDialog>
      <Sheet open={sheet} onClose={() => setSheet(false)} label="Menu">
        <p className="kv-panel-head">Menu</p>
        <p className="mt-3 font-ui text-ui-lg text-ink-2">A modal bottom sheet holds focus until it closes.</p>
        <ActionGroup className="mt-4">
          <Button variant="quiet" onClick={() => setSheet(false)}>Close</Button>
        </ActionGroup>
      </Sheet>
    </>
  );
}

export function StatusSection() {
  return (
    <Section id="status" title="Status, dialogs and empty places" lede="Toasts carry an icon and words. Dialogs put the destructive choice last, in madder, named for what it does. An empty place says what it is for and offers one way forward.">
      <Demo caption="Toasts">
        <div className="grid justify-items-start gap-2">
          {TOASTS.map((record) => (
            <ToastCard key={record.id} toast={record} onDismiss={() => undefined} />
          ))}
        </div>
      </Demo>
      <Demo caption="Live">
        <Overlays />
      </Demo>
      <Grid columns={3}>
        <Demo caption="A list">
          <EmptyState headingLevel={3} title="Your saved list" body="Save a craft or an answer with the bookmark on its page, and it waits here for you." actions={<Button variant="quiet" size="sm">Browse the atlas</Button>} />
        </Demo>
        <Demo caption="A search">
          <EmptyState headingLevel={3} title="No craft or idea matches “xyzzy”" body="Try a material, a method or a place, such as indigo, lost wax or Kerala." actions={<Button variant="quiet" size="sm">Clear the search</Button>} />
        </Demo>
        <Demo caption="One craft">
          <EmptyState
            headingLevel={3}
            plate={<TypographicPlate material="stone" englishName="Agra Marble Inlay" size="small" decorative className="min-h-24" />}
            title="Ask about Agra Marble Inlay"
            body="Start with one of these, or ask your own. Each answer is researched and cited as it is written."
            actions={
              <>
                <Button variant="quiet" size="sm">How is the stone cut and set?</Button>
                <Button variant="quiet" size="sm">Why Agra?</Button>
                <Button variant="quiet" size="sm">What makes the inlay hold?</Button>
              </>
            }
          />
        </Demo>
      </Grid>
      <Grid>
        <Demo caption="Skeleton: monograph opening"><Skeleton shape="masthead" label="Opening the monograph" /></Demo>
        <Demo caption="Skeleton: collection shelf"><Skeleton shape="plateGrid" label="Opening the collection" /></Demo>
        <Demo caption="Skeleton: answer lede"><Skeleton shape="lede" label="Writing the answer" /></Demo>
        <Demo caption="Skeleton: chart"><Skeleton shape="chart" label="Drawing the chart" /></Demo>
      </Grid>
    </Section>
  );
}
